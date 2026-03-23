from __future__ import annotations

from datetime import date
from pathlib import Path

from teletube.config import Config
from teletube.downloader import VideoEntry, process_channel


def test_process_channel_skips_existing(monkeypatch, tmp_path: Path) -> None:
    config = Config(
        channels_file=tmp_path / "channels.txt",
        start_date=date(2026, 1, 1),
        output_root=tmp_path,
    )
    entry = VideoEntry(video_id="abc123", title="Video Title", upload_date=date(2026, 3, 1))

    monkeypatch.setattr("teletube.downloader.list_channel_videos", lambda _channel, _date: [entry])

    target_dir = tmp_path / "@mychannel" / "2026-03-01 Video Title"
    target_dir.mkdir(parents=True)

    called = {"value": False}

    def _unexpected_download(*_args, **_kwargs):
        called["value"] = True

    monkeypatch.setattr("teletube.downloader.download_video", _unexpected_download)

    stats = process_channel("https://www.youtube.com/@mychannel", config)

    assert stats.downloaded == 0
    assert stats.skipped_existing == 1
    assert called["value"] is False

