from __future__ import annotations

from pathlib import Path

import pytest

from teletube.config import ConfigError, load_channels, load_config


def test_load_config_requires_env_vars(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("https://www.youtube.com/@example\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="TELETUBE_START_DATE"):
        load_config(env={"TELETUBE_CHANNELS_FILE": str(channels_file)}, output_root=tmp_path)


def test_load_config_validates_date_format(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("https://www.youtube.com/@example\n", encoding="utf-8")

    env = {
        "TELETUBE_CHANNELS_FILE": str(channels_file),
        "TELETUBE_START_DATE": "2026/01/01",
    }

    with pytest.raises(ConfigError, match="YYYY-MM-DD"):
        load_config(env=env, output_root=tmp_path)


def test_load_channels_ignores_empty_lines(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("\nhttps://www.youtube.com/@a\n\nhttps://www.youtube.com/@b\n", encoding="utf-8")

    assert load_channels(channels_file) == [
        "https://www.youtube.com/@a",
        "https://www.youtube.com/@b",
    ]


def test_load_channels_fails_if_none(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("\n\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="No channels found"):
        load_channels(channels_file)

