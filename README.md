# Teletube

Teletube is a small Python CronJob-style downloader that fetches YouTube channel videos with `yt-dlp` and stores them as:

```text
<output-root>/<channel>/<YYYY-MM-DD title>/
```

Each downloaded video directory contains a `folder.jpg` thumbnail.

## Environment variables

- `TELETUBE_CHANNELS_FILE` (required): file with one channel per line.
- `TELETUBE_START_DATE` (required): lower-bound publish date in `YYYY-MM-DD` format.
- `TELETUBE_DESTINATION_ROOT` (required): destination root directory where channel folders are created.

## Quick start

```bash
python -m pip install -r requirements.txt
export TELETUBE_CHANNELS_FILE=/path/to/channels.txt
export TELETUBE_START_DATE=2026-01-01
export TELETUBE_DESTINATION_ROOT=/data
python -m teletube
```

## Run tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

