from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


class ConfigError(ValueError):
    """Raised when required environment configuration is invalid."""


@dataclass(frozen=True)
class Config:
    channels_file: Path
    start_date: date
    output_root: Path


def _require_env(name: str, env: dict[str, str] | None = None) -> str:
    source = env if env is not None else os.environ
    raw = source.get(name)
    if raw is None or not raw.strip():
        raise ConfigError(f"Missing required environment variable: {name}")
    return raw.strip()


def _parse_start_date(raw: str) -> date:
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ConfigError(
            "Invalid TELETUBE_START_DATE. Expected strict format YYYY-MM-DD"
        ) from exc


def _parse_channels_file(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.exists():
        raise ConfigError(f"TELETUBE_CHANNELS_FILE does not exist: {path}")
    if not path.is_file():
        raise ConfigError(f"TELETUBE_CHANNELS_FILE is not a file: {path}")
    return path


def load_config(env: dict[str, str] | None = None, output_root: Path | None = None) -> Config:
    channels_file_raw = _require_env("TELETUBE_CHANNELS_FILE", env)
    start_date_raw = _require_env("TELETUBE_START_DATE", env)

    channels_file = _parse_channels_file(channels_file_raw)
    start_date = _parse_start_date(start_date_raw)

    root = output_root if output_root is not None else Path.cwd()
    return Config(channels_file=channels_file, start_date=start_date, output_root=root)


def load_channels(channels_file: Path) -> list[str]:
    channels: list[str] = []
    for line in channels_file.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value:
            continue
        channels.append(value)
    if not channels:
        raise ConfigError(f"No channels found in {channels_file}")
    return channels

