from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, ElementTree

from .config import Config, load_channels
from .naming import build_video_dir, parse_upload_date, video_file_base


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
    command = ["yt-dlp", *args]
    return subprocess.run(command, check=True, text=True, capture_output=True)


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


def _rename_thumbnail_to_expected_name(video_dir: Path, video_file_base: str) -> None:
    """Rename a downloaded thumbnail to match the video filename pattern.
    
    Looks for *.jpg files (excluding the target), keeps the most recent one,
    and renames it to {video_file_base}.jpg.
    """
    target_name = f"{video_file_base}.jpg"
    jpgs = [
        p
        for p in video_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"} and p.name != target_name
    ]
    if not jpgs:
        return
    thumb = max(jpgs, key=lambda p: p.stat().st_mtime)
    target = video_dir / target_name
    if thumb != target:
        shutil.move(str(thumb), str(target))


def _create_nfo_file(video_dir: Path, video_file_base: str, entry: VideoEntry) -> None:
    """Create a Jellyfin-compatible NFO metadata file for the video.
    
    Jellyfin expects episodedetails.nfo for videos organized by season.
    Reference: https://jellyfin.org/docs/general/server/metadata/nfo/
    """
    nfo_path = video_dir / f"{video_file_base}.nfo"
    
    # Create episode details XML structure
    episode = Element("episodedetails")
    
    title_elem = Element("title")
    title_elem.text = entry.title
    episode.append(title_elem)
    
    plot_elem = Element("plot")
    plot_elem.text = f"YouTube video from {entry.upload_date.isoformat()}"
    episode.append(plot_elem)
    
    aired_elem = Element("aired")
    aired_elem.text = entry.upload_date.isoformat()
    episode.append(aired_elem)
    
    uniqueid_elem = Element("uniqueid")
    uniqueid_elem.set("type", "youtube")
    uniqueid_elem.text = entry.video_id
    episode.append(uniqueid_elem)
    
    # Write XML with proper declaration
    tree = ElementTree(episode)
    tree.write(nfo_path, encoding="utf-8", xml_declaration=True)


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

    _rename_thumbnail_to_expected_name(destination, base_name)
    _create_nfo_file(destination, base_name, entry)


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
