from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .config import Config, load_channels
from .naming import build_video_dir, parse_upload_date


class DownloadError(RuntimeError):
    """Raised when yt-dlp returns malformed data or fails."""


@dataclass(frozen=True)
class VideoEntry:
    video_id: str
    title: str
    upload_date: date


@dataclass(frozen=True)
class RunStats:
    downloaded: int = 0
    skipped_existing: int = 0
    skipped_old_or_invalid: int = 0


def run_yt_dlp(args: list[str]) -> subprocess.CompletedProcess[str]:
    command = ["yt-dlp", "--remote-components ejs:github", *args]
    return subprocess.run(command, check=True, text=True, capture_output=True)


def _parse_channel_entries(payload: str, start_date: date) -> list[VideoEntry]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DownloadError("yt-dlp did not return valid JSON") from exc

    raw_entries: list[dict[str, Any]] = data.get("entries") or []
    entries: list[VideoEntry] = []

    for item in raw_entries:
        video_id = (item.get("id") or "").strip()
        title = (item.get("title") or "").strip()
        raw_upload_date = (item.get("upload_date") or "").strip()
        if not video_id or not title or not raw_upload_date:
            continue
        try:
            upload_date = parse_upload_date(raw_upload_date)
        except ValueError:
            continue
        if upload_date < start_date:
            continue
        entries.append(VideoEntry(video_id=video_id, title=title, upload_date=upload_date))

    return entries


def list_channel_videos(channel: str, start_date: date) -> list[VideoEntry]:
    result = run_yt_dlp(["--dump-single-json", channel])
    return _parse_channel_entries(result.stdout, start_date)


def _rename_thumbnail_to_folder_jpg(video_dir: Path) -> None:
    jpgs = [
        p
        for p in video_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"} and p.name != "folder.jpg"
    ]
    if not jpgs:
        return
    thumb = max(jpgs, key=lambda p: p.stat().st_mtime)
    target = video_dir / "folder.jpg"
    if thumb != target:
        shutil.move(str(thumb), str(target))


def download_video(channel: str, entry: VideoEntry, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    video_url = f"https://www.youtube.com/watch?v={entry.video_id}"

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
            str(destination / "video.%(ext)s"),
            video_url,
        ]
    )

    _rename_thumbnail_to_folder_jpg(destination)


def process_channel(channel: str, config: Config) -> RunStats:
    downloaded = 0
    skipped_existing = 0
    skipped_old_or_invalid = 0

    for entry in list_channel_videos(channel, config.start_date):
        target_dir = build_video_dir(config.output_root, channel, entry.upload_date, entry.title)
        if target_dir.exists():
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
