FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache ffmpeg tini deno

COPY requirements.txt /app/
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY teletube /app/teletube
COPY README.md AGENTS.md /app/

ENTRYPOINT ["/sbin/tini", "-v", "-g", "--", "python", "-m", "teletube"]

