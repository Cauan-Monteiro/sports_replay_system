from collections import deque
from datetime import datetime
from fastapi import FastAPI, HTTPException
import os

# UDP perde pacotes atravessando a rede do Docker - forcar TCP.
# Precisa estar definido antes do OpenCV carregar o backend do ffmpeg.
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")

import cv2 as cv
import threading
import time
import uvicorn
import socket

FONTE = os.getenv("RTSP_URL", "rtsp://hsaa:5wrrrd@192.168.0.92:554/stream")
FPS = float(os.getenv("FPS", "30"))
BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", "300"))
PASTA_CLIPS = os.getenv(
    "CLIPS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clips')
)
HEADLESS = os.getenv("HEADLESS", "0") == "1"

# Sem display nao ha como abrir a janela, entao a fonte so pode cair e voltar
# sozinha - tenta reconectar antes de desistir.
MAX_TENTATIVAS = int(os.getenv("MAX_TENTATIVAS", "10"))
ESPERA_RECONEXAO = float(os.getenv("ESPERA_RECONEXAO", "3"))

buffer_frames = deque(maxlen=BUFFER_SIZE)
buffer_lock = threading.Lock()

app = FastAPI(title="Replay System")


class BufferVazioError(Exception):
    pass


def salvar_replay():
    """Grava os frames do buffer circular em um mp4 e devolve os dados do clipe."""
    with buffer_lock:
        frames = list(buffer_frames)

    if not frames:
        raise BufferVazioError()

    altura, largura, _ = frames[0].shape

    now = datetime.now()
    nome_arquivo = now.strftime("replay_%Y-%m-%d_%H-%M-%S.mp4")
    rota_pasta = os.path.join(PASTA_CLIPS, now.strftime("%H"))
    os.makedirs(rota_pasta, exist_ok=True)
    caminho_final = os.path.join(rota_pasta, nome_arquivo)

    fourcc = cv.VideoWriter_fourcc(*'mp4v')
    out = cv.VideoWriter(caminho_final, fourcc, FPS, (largura, altura))
    for f in frames:
        out.write(f)
    out.release()

    print(f"Captura finalizada na pasta: {caminho_final}!")

    return {
        "status": "OK",
        "horario": now.isoformat(),
        "arquivo": caminho_final,
        "frames": len(frames),
    }


@app.get("/replay")
def trigger_replay():
    print("Gravando os ultimos 30s...")
    try:
        return salvar_replay()
    except BufferVazioError:
        raise HTTPException(status_code=409, detail="Buffer vazio - captura ainda nao iniciou")


@app.get("/health")
def health():
    with buffer_lock:
        total = len(buffer_frames)
    return {"status": "OK", "frames_no_buffer": total}


def iniciar_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return thread


def capturar(cap):
    """Alimenta o buffer ate o stream cair. Devolve True se o usuario pediu para sair."""
    while True:
        # Capture frame-by-frame
        success, frame = cap.read()

        # if frame is read correctly ret is True
        if not success:
            print("Can't receive frame (stream end?).")
            return False

        with buffer_lock:
            buffer_frames.append(frame)

        if HEADLESS:
            continue

        # Display the resulting frame
        cv.imshow('frame', frame)

        key = cv.waitKey(1) & 0xFF

        if key == ord('r'):
            print("Gravando os ultimos 30s...")
            try:
                salvar_replay()
            except BufferVazioError:
                print("Buffer vazio - nada a gravar.")

        if key == ord('q'):
            return True


def main():
    # Pega o nome do computador
    nome_host = socket.gethostname()
    # Pega o IP correspondente ao nome
    ip_local = socket.gethostbyname(nome_host)

    print("="*30)
    print("REPLAY SYSTEM")
    print(f"Nome do host: {nome_host}")
    print(f"IP Local: {ip_local}")
    print(f"Modo: {'headless' if HEADLESS else 'janela'}")
    print("="*30)

    iniciar_api()

    tentativas = 0

    try:
        while True:
            cap = cv.VideoCapture(FONTE)

            if not cap.isOpened():
                cap.release()

                if not HEADLESS:
                    print("Cannot open camera")
                    return

                tentativas += 1
                if tentativas > MAX_TENTATIVAS:
                    print(f"Fonte inacessivel apos {MAX_TENTATIVAS} tentativas. Encerrando.")
                    return

                print(f"Falha ao abrir a fonte - nova tentativa em {ESPERA_RECONEXAO}s "
                      f"({tentativas}/{MAX_TENTATIVAS})")
                time.sleep(ESPERA_RECONEXAO)
                continue

            print("Conectado a fonte.")
            tentativas = 0

            try:
                if capturar(cap):
                    return
            finally:
                cap.release()

            if not HEADLESS:
                return

            print(f"Reconectando em {ESPERA_RECONEXAO}s...")
            time.sleep(ESPERA_RECONEXAO)
    finally:
        if not HEADLESS:
            cv.destroyAllWindows()


if __name__ == "__main__":
    main()
