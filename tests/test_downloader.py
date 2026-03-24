from __future__ import annotations

import json
from datetime import date

import pytest

from teletube.downloader import DownloadError, _parse_channel_entries


def _make_channel_payload(videos: list[dict], extra_tabs: list[dict] | None = None) -> str:
    tabs = [{"title": "Videos", "entries": videos}]
    if extra_tabs:
        tabs.extend(extra_tabs)
    return json.dumps({"entries": tabs})


def test_parses_videos_from_videos_tab() -> None:
    payload = _make_channel_payload(
        videos=[
            {"id": "abc1", "title": "First Video", "upload_date": "20260301", "description": "First desc"},
            {"id": "abc2", "title": "Second Video", "upload_date": "20260302", "description": "Second desc"},
        ]
    )
    entries = _parse_channel_entries(payload, start_date=date(2026, 1, 1))
    assert [e.video_id for e in entries] == ["abc1", "abc2"]
    assert entries[0].description == "First desc"
    assert entries[1].description == "Second desc"


def test_ignores_shorts_tab() -> None:
    payload = json.dumps({
        "entries": [
            {"title": "Videos", "entries": [{"id": "v1", "title": "A", "upload_date": "20260301", "description": ""}]},
            {"title": "Shorts", "entries": [{"id": "s1", "title": "Short", "upload_date": "20260301", "description": ""}]},
        ]
    })
    entries = _parse_channel_entries(payload, start_date=date(2026, 1, 1))
    assert [e.video_id for e in entries] == ["v1"]


def test_skips_videos_older_than_start_date() -> None:
    payload = _make_channel_payload(
        videos=[
            {"id": "old", "title": "Old Video", "upload_date": "20251231", "description": ""},
            {"id": "new", "title": "New Video", "upload_date": "20260101", "description": ""},
        ]
    )
    entries = _parse_channel_entries(payload, start_date=date(2026, 1, 1))
    assert [e.video_id for e in entries] == ["new"]


def test_skips_entries_missing_fields() -> None:
    payload = _make_channel_payload(
        videos=[
            {"id": "ok", "title": "Good", "upload_date": "20260301", "description": "desc"},
            {"id": "", "title": "No ID", "upload_date": "20260301", "description": ""},
            {"id": "nod", "title": "", "upload_date": "20260301", "description": ""},
            {"id": "nou", "title": "No Date", "upload_date": "", "description": ""},
        ]
    )
    entries = _parse_channel_entries(payload, start_date=date(2026, 1, 1))
    assert [e.video_id for e in entries] == ["ok"]


def test_raises_on_invalid_json() -> None:
    with pytest.raises(DownloadError, match="valid JSON"):
        _parse_channel_entries("not json", start_date=date(2026, 1, 1))


def test_fallback_when_no_videos_tab() -> None:
    payload = json.dumps({
        "entries": [
            {"title": "Live", "entries": [{"id": "live1", "title": "Stream", "upload_date": "20260301", "description": ""}]},
        ]
    })
    entries = _parse_channel_entries(payload, start_date=date(2026, 1, 1))
    assert [e.video_id for e in entries] == ["live1"]

