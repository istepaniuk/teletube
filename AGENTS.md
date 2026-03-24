# AGENTS.md

## Purpose and scope
This is the single source of truth for Teletube product behavior and 
coding-agent workflow.

Teletube is a simple Python video downloader that uses `yt-dlp` to fetch 
YouTube channel videos into a local library. The goal is to keep a library of 
YouTube videos which is ready be consumed using Jellyfin.

## Product contract (must preserve)
- Read channels from `TELETUBE_CHANNELS_FILE` (one channel per line).
- Read start date from `TELETUBE_START_DATE` in strict `YYYY-MM-DD` format.
- Read destination root from `TELETUBE_DESTINATION_ROOT` (mandatory existing directory).
- Fail fast with clear errors when required env vars are missing or malformed.
- Only download videos not already present (idempotent reruns).
- Skip videos older than `TELETUBE_START_DATE`.
- Download with best available quality up to 1080p.
- Instruct `yt-dlp` to convert the thumbnail to JPEG and store it alongside the 
  video file (same base name).
- Keep output layout as `@ChannelName/Season YY/<YYYY-MM-DD-video_id>.<ext>` 
  (Jellyfin-compatible).
- Generate Jellyfin metadata `.nfo` file with episode details (title, date, video ID).
- Use the video description metadata to populate the plot tag in the `.nfo` file.
- Use the day of the year to assign an episode number in the .nfo data.


## AI-friendly repository structure
Use this layout when implementing the project:

```text
.
├── AGENTS.md
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── teletube/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── naming.py
│   ├── nfo.py
│   └── downloader.py
├── tests/
│   ├── test_config.py
│   ├── test_naming.py
│   ├── test_nfo.py
│   └── test_idempotency.py
└── kubernetes/
    ├── cronjob.yaml
    └── configmap.yaml
```

## Design constraints
- Keep logic stateless between runs (hourly Kubernetes CronJob model).
- Runs must be idempotent.
- Keep config parsing centralized in `teletube/config.py`.
- Keep naming/date rules centralized in `teletube/naming.py`.
- Keep Jellyfin `.nfo` generation centralized in `teletube/nfo.py`.
- Keep `yt-dlp` invocation isolated in `teletube/downloader.py`.

## Implementation workflow for agents
1. Add minimal code that satisfies the product contract first.
2. Add or update tests for date validation, output naming, and idempotent skips.
3. Keep Docker and Kubernetes files aligned with env var contract.
4. Prefer small, reviewable patches over broad speculative architecture.

## Change-management rules
- Any behavior change must be reflected in this file in the same PR.
- Document intentional deviations from current contract in PR notes.
- Do not invent undocumented behavior; implement the smallest compatible behavior.

## Known runtime assumptions
- Containerized deployment with root-level `Dockerfile` (Alpine base expected).
- Scheduled execution via Kubernetes CronJob in `kubernetes/`.
- A ConfigMap contains the list of channels to download and is mounted.
- No long-lived process state or external metadata store is required.
