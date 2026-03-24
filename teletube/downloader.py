from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .config import Config, load_channels
from .naming import build_video_dir, channel_folder_name, parse_upload_date, video_file_base
from .nfo import create_nfo_file, create_tvshow_nfo_file


class DownloadError(RuntimeError):
    """Raised when yt-dlp returns malformed data or fails."""


@dataclass(frozen=True)
class VideoEntry:
    video_id: str
    title: str
    upload_date: date
    description: str = ""


@dataclass(frozen=True)
class ChannelMetadata:
    title: str
    description: str = ""
    avatar_url: str = ""
    banner_url: str = ""


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


def _pick_image_url(data: dict[str, Any], direct_keys: list[str], id_keywords: list[str]) -> str:
    for key in direct_keys:
        value = (data.get(key) or "").strip()
        if value:
            return value

    thumbnails = data.get("thumbnails") or []
    if not isinstance(thumbnails, list):
        return ""

    for thumb in thumbnails:
        if not isinstance(thumb, dict):
            continue
        thumb_id = (thumb.get("id") or "").strip().lower()
        thumb_url = (thumb.get("url") or "").strip()
        if not thumb_url:
            continue
        if any(keyword in thumb_id for keyword in id_keywords):
            return thumb_url

    return ""


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


def _parse_channel_metadata(payload: str, channel: str) -> ChannelMetadata:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise DownloadError("yt-dlp did not return valid JSON") from exc

    title = (
        (data.get("channel") or "").strip()
        or (data.get("uploader") or "").strip()
        or (data.get("title") or "").strip()
        or channel_folder_name(channel)
    )
    description = ((data.get("description") or "").strip() or (data.get("channel_description") or "").strip())

    avatar_url = _pick_image_url(
        data,
        direct_keys=["channel_avatar", "uploader_avatar", "avatar"],
        id_keywords=["avatar", "profile", "channel"],
    )
    banner_url = _pick_image_url(
        data,
        direct_keys=["channel_banner", "banner"],
        id_keywords=["banner", "header"],
    )

    return ChannelMetadata(
        title=title,
        description=description,
        avatar_url=avatar_url,
        banner_url=banner_url,
    )


def list_channel_videos(channel: str, start_date: date) -> list[VideoEntry]:
    result = run_yt_dlp(["--dump-single-json", "--playlist-end", "10", channel])
    return _parse_channel_entries(result.stdout, start_date)


def list_channel_metadata(channel: str) -> ChannelMetadata:
    result = run_yt_dlp(["--dump-single-json", "--playlist-end", "1", channel])
    return _parse_channel_metadata(result.stdout, channel)


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

    channel_dir = config.output_root / channel_folder_name(channel)
    channel_metadata = list_channel_metadata(channel)
    create_tvshow_nfo_file(
        channel_dir=channel_dir,
        title=channel_metadata.title,
        description=channel_metadata.description,
        avatar_url=channel_metadata.avatar_url,
        banner_url=channel_metadata.banner_url,
    )

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
