from __future__ import annotations

from datetime import date
from pathlib import Path

from teletube.config import Config
from teletube.downloader import ChannelMetadata, VideoEntry, process_channel
from teletube.naming import video_file_base


def test_process_channel_skips_existing(monkeypatch, tmp_path: Path) -> None:
    config = Config(
        channels_file=tmp_path / "channels.txt",
        start_date=date(2026, 1, 1),
        output_root=tmp_path,
    )
    entry = VideoEntry(
        video_id="abc123",
        title="Video Title",
        upload_date=date(2026, 3, 1),
        description="This is a test video",
    )

    monkeypatch.setattr("teletube.downloader.list_channel_videos", lambda _channel, _date: [entry])
    monkeypatch.setattr(
        "teletube.downloader.list_channel_metadata",
        lambda _channel: ChannelMetadata(title="@mychannel"),
    )

    # Create the video file to simulate it already being downloaded
    video_dir = tmp_path / "@mychannel" / "Season 26"
    video_dir.mkdir(parents=True)
    base_name = video_file_base(date(2026, 3, 1), "abc123")
    video_file = video_dir / f"{base_name}.mp4"
    video_file.write_text("fake video", encoding="utf-8")

    called = {"value": False}

    def _unexpected_download(*_args, **_kwargs):
        called["value"] = True

    monkeypatch.setattr("teletube.downloader.download_video", _unexpected_download)

    stats = process_channel("https://www.youtube.com/@mychannel", config)

    assert stats.downloaded == 0
    assert stats.skipped_existing == 1
    assert called["value"] is False


def test_process_channel_writes_channel_tvshow_nfo(monkeypatch, tmp_path: Path) -> None:
    config = Config(
        channels_file=tmp_path / "channels.txt",
        start_date=date(2026, 1, 1),
        output_root=tmp_path,
    )

    monkeypatch.setattr("teletube.downloader.list_channel_videos", lambda _channel, _date: [])
    monkeypatch.setattr(
        "teletube.downloader.list_channel_metadata",
        lambda _channel: ChannelMetadata(
            title="@mychannel",
            description="Channel bio",
            avatar_url="https://img.example/avatar.jpg",
            banner_url="https://img.example/banner.jpg",
        ),
    )

    stats = process_channel("https://www.youtube.com/@mychannel", config)

    assert stats.downloaded == 0
    tvshow_nfo_path = tmp_path / "@mychannel" / "tvshow.nfo"
    assert tvshow_nfo_path.exists()


