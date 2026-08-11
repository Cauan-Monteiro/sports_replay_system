FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ffmpeg: backend de video do OpenCV (RTSP + escrita mp4)
# libglib2.0-0: dependencia nativa do opencv-python-headless
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

RUN useradd --create-home --uid 1000 replay \
    && mkdir -p /app/clips \
    && chown -R replay:replay /app
USER replay

EXPOSE 8000

CMD ["python", "main.py"]
