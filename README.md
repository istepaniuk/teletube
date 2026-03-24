# Teletube

Teletube is a small Python media downloader that fetches YouTube channel videos 
with `yt-dlp` and stores them in a Jellyfin-compatible layout with metadata:

```text
<output-root>/
  <channel>/
    Season <YY>/
      <YYYY-MM-DD-video_id>.mp4
      <YYYY-MM-DD-video_id>.jpg
      <YYYY-MM-DD-video_id>.nfo
```

Each video is stored with:
- **Video file**: `<YYYY-MM-DD-video_id>.mp4` (or other ext from yt-dlp)
- **Thumbnail**: `<YYYY-MM-DD-video_id>.jpg` — poster image for Jellyfin
- **Metadata**: `<YYYY-MM-DD-video_id>.nfo` — Jellyfin episode details 
  (title, air date, description, YouTube ID)

## Module responsibilities

- `teletube/config.py`: environment parsing and validation.
- `teletube/naming.py`: output naming and date parsing rules.
- `teletube/nfo.py`: Jellyfin `.nfo` generation.
- `teletube/downloader.py`: `yt-dlp` listing/download orchestration.

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

