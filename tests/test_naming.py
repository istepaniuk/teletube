from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from teletube.naming import build_video_dir, channel_folder_name, parse_upload_date, video_folder_name


def test_parse_upload_date_accepts_yyyymmdd() -> None:
    assert parse_upload_date("20260301") == date(2026, 3, 1)


def test_parse_upload_date_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_upload_date("2026-03-01")


def test_channel_folder_name_from_url() -> None:
    assert channel_folder_name("https://www.youtube.com/@mychannel") == "@mychannel"


def test_video_folder_name_format() -> None:
    assert video_folder_name(date(2026, 3, 1), "Hello/World") == "2026-03-01 Hello World"


def test_build_video_dir_layout() -> None:
    root = Path("/library")
    path = build_video_dir(root, "https://www.youtube.com/@mychannel", date(2026, 3, 1), "A Video")
    assert str(path) == "/library/@mychannel/2026-03-01 A Video"

