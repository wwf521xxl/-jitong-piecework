FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JITONG_DATA_DIR=/data \
    JITONG_HOST=0.0.0.0 \
    JITONG_PORT=8787 \
    JITONG_COOKIE_SECURE=1

WORKDIR /app

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server ./server
COPY app ./app

RUN mkdir -p /data
VOLUME ["/data"]
EXPOSE 8787

CMD ["python", "-m", "server.main"]
