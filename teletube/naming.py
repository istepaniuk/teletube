from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import re
from urllib.parse import urlparse


def parse_upload_date(raw: str) -> date:
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError as exc:
        raise ValueError(f"Invalid upload_date from yt-dlp: {raw}") from exc


def sanitize_title(title: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\x00-\x1f]", " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "untitled"


def channel_folder_name(channel: str) -> str:
    parsed = urlparse(channel)
    if parsed.scheme and parsed.netloc:
        path_bits = [bit for bit in parsed.path.split("/") if bit]
        if path_bits:
            return sanitize_title(path_bits[-1])
        return sanitize_title(parsed.netloc)
    return sanitize_title(channel)


def season_folder_name(upload_date: date) -> str:
    """Return the season folder name based on upload year."""
    return f"Season {upload_date.strftime("%y")}"


def video_file_base(upload_date: date, video_id: str) -> str:
    """Return the base filename for a video (without extension).
    
    Format: YYYY-MM-DD video_id
    Used for both video and thumbnail files.
    """
    return f"{upload_date.isoformat()}-{video_id}"


def build_video_dir(output_root: Path, channel: str, upload_date: date, video_id: str) -> Path:
    """Return the directory where video and thumbnail files should be stored.
    
    Structure: <output_root>/<channel>/Season <YYYY>/
    Individual files within this directory follow the pattern: <YYYY-MM-DD video_id>.<ext>
    """
    return output_root / channel_folder_name(channel) / season_folder_name(upload_date)

