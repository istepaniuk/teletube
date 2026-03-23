from __future__ import annotations

import sys

from .config import ConfigError, load_config
from .downloader import DownloadError, run


def main() -> int:
    try:
        config = load_config()
        stats = run(config)
    except (ConfigError, DownloadError) as exc:
        print(f"teletube error: {exc}", file=sys.stderr)
        return 1

    print(
        "teletube finished: "
        f"downloaded={stats.downloaded} "
        f"skipped_existing={stats.skipped_existing}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

