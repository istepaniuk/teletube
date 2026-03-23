from __future__ import annotations

from pathlib import Path

import pytest

from teletube.config import ConfigError, load_channels, load_config


def test_load_config_requires_env_vars(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("https://www.youtube.com/@example\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="TELETUBE_START_DATE"):
        load_config(env={"TELETUBE_CHANNELS_FILE": str(channels_file)})


def test_load_config_validates_date_format(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("https://www.youtube.com/@example\n", encoding="utf-8")

    env = {
        "TELETUBE_CHANNELS_FILE": str(channels_file),
        "TELETUBE_START_DATE": "2026/01/01",
        "TELETUBE_DESTINATION_ROOT": str(tmp_path),
    }

    with pytest.raises(ConfigError, match="YYYY-MM-DD"):
        load_config(env=env)


def test_load_config_requires_destination_root(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("https://www.youtube.com/@example\n", encoding="utf-8")

    env = {
        "TELETUBE_CHANNELS_FILE": str(channels_file),
        "TELETUBE_START_DATE": "2026-01-01",
    }

    with pytest.raises(ConfigError, match="TELETUBE_DESTINATION_ROOT"):
        load_config(env=env)


def test_load_config_validates_destination_root_directory(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("https://www.youtube.com/@example\n", encoding="utf-8")
    not_a_dir = tmp_path / "file.txt"
    not_a_dir.write_text("x", encoding="utf-8")

    env = {
        "TELETUBE_CHANNELS_FILE": str(channels_file),
        "TELETUBE_START_DATE": "2026-01-01",
        "TELETUBE_DESTINATION_ROOT": str(not_a_dir),
    }

    with pytest.raises(ConfigError, match="not a directory"):
        load_config(env=env)


def test_load_config_uses_destination_root(tmp_path: Path) -> None:
    channels_file = tmp_path / "channels.txt"
    channels_file.write_text("https://www.youtube.com/@example\n", encoding="utf-8")
    output_root = tmp_path / "library"
    output_root.mkdir()

    env = {
        "TELETUBE_CHANNELS_FILE": str(channels_file),
        "TELETUBE_START_DATE": "2026-01-01",
        "TELETUBE_DESTINATION_ROOT": str(output_root),
    }

    config = load_config(env=env)

    assert config.output_root == output_root


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

