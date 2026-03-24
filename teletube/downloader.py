from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from teletube.config import Config, load_channels
from teletube.naming import build_video_dir, parse_upload_date, video_file_base
from teletube.nfo import create_nfo_file


class DownloadError(RuntimeError):
    """Raised when yt-dlp returns malformed data or fails."""


@dataclass(frozen=True)
class VideoEntry:
    video_id: str
    title: str
    upload_date: date
    description: str = ""


@dataclass(frozen=True)
class RunStats:
    downloaded: int = 0
    skipped_existing: int = 0
    skipped_old_or_invalid: int = 0


def run_yt_dlp(args: list[str]) -> subprocess.CompletedProcess[str]:
    command = ["yt-dlp", "--cache-dir", "/tmp", "--remote-components", "ejs:github", *args]
    print("- Running:", " ".join(command))
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result


def _find_videos_playlist(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the raw video entries from the 'Videos' playlist tab.

    Channel JSON returned by yt-dlp has the shape:
        { "entries": [ { "title": "Videos", "entries": [...] },
                       { "title": "Shorts", "entries": [...] }, ... ] }
    We want only the 'Videos' tab. Fall back to the first tab that has
    nested entries if no tab is explicitly titled 'Videos'.
    """
    tabs: list[dict[str, Any]] = data.get("entries") or []
    for tab in tabs:
        if (tab.get("title") or "").strip().lower() == "videos":
            return tab.get("entries") or []
    # fallback: first tab that itself contains entries (not flat video dicts)
    for tab in tabs:
        nested = tab.get("entries")
        if isinstance(nested, list):
            return nested
    return []


def _parse_channel_entries(payload: str, start_date: date) -> list[VideoEntry]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DownloadError("yt-dlp did not return valid JSON") from exc

    raw_videos = _find_videos_playlist(data)
    entries: list[VideoEntry] = []

    for item in raw_videos:
        video_id = (item.get("id") or "").strip()
        title = (item.get("title") or "").strip()
        raw_upload_date = (item.get("upload_date") or "").strip()
        description = (item.get("description") or "").strip()
        if not video_id or not title or not raw_upload_date:
            continue
        try:
            upload_date = parse_upload_date(raw_upload_date)
        except ValueError:
            continue
        if upload_date < start_date:
            continue
        entries.append(
            VideoEntry(
                video_id=video_id,
                title=title,
                upload_date=upload_date,
                description=description,
            )
        )

    return entries


def list_channel_videos(channel: str, start_date: date) -> list[VideoEntry]:
    result = run_yt_dlp(["--dump-single-json", "--playlist-end", "10", channel])
    return _parse_channel_entries(result.stdout, start_date)


def download_video(channel: str, entry: VideoEntry, destination: Path) -> None:
    """Download a video and its thumbnail to the destination directory.
    
    Video filename pattern: {YYYY-MM-DD video_id}.mp4 (or other ext from yt-dlp)
    Thumbnail: {YYYY-MM-DD video_id}.jpg
    Metadata: {YYYY-MM-DD video_id}.nfo
    """
    destination.mkdir(parents=True, exist_ok=True)
    video_url = f"https://www.youtube.com/watch?v={entry.video_id}"

    # Use video_file_base for output filename pattern
    base_name = video_file_base(entry.upload_date, entry.video_id)

    run_yt_dlp(
        [
            "--no-progress",
            "-f",
            "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
            "--merge-output-format",
            "mp4",
            "--write-thumbnail",
            "--convert-thumbnails",
            "jpg",
            "-o",
            str(destination / f"{base_name}.%(ext)s"),
            video_url,
        ]
    )

    create_nfo_file(
        video_dir=destination,
        base_name=base_name,
        title=entry.title,
        upload_date=entry.upload_date,
        video_id=entry.video_id,
        description=entry.description,
    )


def process_channel(channel: str, config: Config) -> RunStats:
    downloaded = 0
    skipped_existing = 0
    skipped_old_or_invalid = 0

    for entry in list_channel_videos(channel, config.start_date):
        target_dir = build_video_dir(config.output_root, channel, entry.upload_date, entry.video_id)
        # Check if video file already exists (using video_id-based naming)
        base_name = video_file_base(entry.upload_date, entry.video_id)
        existing_files = list(target_dir.glob(f"{base_name}.*")) if target_dir.exists() else []
        if existing_files:
            skipped_existing += 1
            continue
        try:
            download_video(channel, entry, target_dir)
        except subprocess.CalledProcessError as exc:
            raise DownloadError(f"yt-dlp failed for {entry.video_id}: {exc.stderr}") from exc
        downloaded += 1

    return RunStats(
        downloaded=downloaded,
        skipped_existing=skipped_existing,
        skipped_old_or_invalid=skipped_old_or_invalid,
    )


def run(config: Config) -> RunStats:
    channels = load_channels(config.channels_file)

    downloaded = 0
    skipped_existing = 0
    skipped_old_or_invalid = 0
    for channel in channels:
        stats = process_channel(channel, config)
        downloaded += stats.downloaded
        skipped_existing += stats.skipped_existing
        skipped_old_or_invalid += stats.skipped_old_or_invalid

    return RunStats(
        downloaded=downloaded,
        skipped_existing=skipped_existing,
        skipped_old_or_invalid=skipped_old_or_invalid,
    )
