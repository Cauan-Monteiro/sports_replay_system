from collections import deque
from sqlite3 import Date
from turtle import delay
import datetime
import cv2 as cv

def __main__():
    print("="*30)
    print("REPLAY SYSTEM")
    print("="*30)

    cap = cv.VideoCapture(0)
    buffer_frames = deque(maxlen=300)
    
    if not cap.isOpened():
        print("Cannot open camera")
        exit()
    while True:
        # Capture frame-by-frame
        success, frame = cap.read()

        # if frame is read correctly ret is True
        if not success:
            print("Can't receive frame (stream end?). Exiting ...")
            break

        buffer_frames.append(frame)

        # Display the resulting frame
        cv.imshow('frame', frame)

        if cv.waitKey(1) == ord('r'):
            print("Gravando os ultimos 30s...")
            # Pegamos a altura e largura do frame atual para configurar o vídeo
            altura, largura, _ = frame.shape 

            # Configuramos o arquivo de saída chamado 'replay.mp4'
            fourcc = cv.VideoWriter_fourcc(*'mp4v')
            out = cv.VideoWriter('replay.mp4', fourcc, 30.0, (largura, altura))
            for f in buffer_frames:
                out.write(f)

            cap.release()
            break

        if cv.waitKey(1) == ord('q'):
            break


__main__()
