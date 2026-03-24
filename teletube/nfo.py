from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree

__all__ = ["create_nfo_file", "create_tvshow_nfo_file"]


def create_nfo_file(
    video_dir: Path,
    base_name: str,
    title: str,
    upload_date: date,
    video_id: str,
    description: str = "",
) -> None:
    """Create a Jellyfin-compatible NFO metadata file for a video."""
    nfo_path = video_dir / f"{base_name}.nfo"

    episode = Element("episodedetails")

    title_elem = Element("title")
    title_elem.text = title
    episode.append(title_elem)

    episode_num_elem = Element("episode")
    episode_num_elem.text = upload_date.strftime("%j")
    episode.append(episode_num_elem)

    plot_elem = Element("plot")
    plot_elem.text = description or f"YouTube video from {upload_date.isoformat()}"
    episode.append(plot_elem)

    aired_elem = Element("aired")
    aired_elem.text = upload_date.isoformat()
    episode.append(aired_elem)

    uniqueid_elem = Element("uniqueid")
    uniqueid_elem.set("type", "youtube")
    uniqueid_elem.text = video_id
    episode.append(uniqueid_elem)

    tree = ElementTree(episode)
    tree.write(nfo_path, encoding="utf-8", xml_declaration=True)


def create_tvshow_nfo_file(
    channel_dir: Path,
    title: str,
    description: str = "",
    avatar_url: str = "",
    banner_url: str = "",
) -> None:
    """Create a Jellyfin-compatible tvshow.nfo file for channel-level metadata."""
    channel_dir.mkdir(parents=True, exist_ok=True)
    nfo_path = channel_dir / "tvshow.nfo"

    tvshow = Element("tvshow")

    title_elem = Element("title")
    title_elem.text = title
    tvshow.append(title_elem)

    if description:
        plot_elem = Element("plot")
        plot_elem.text = description
        tvshow.append(plot_elem)

    if avatar_url:
        thumb_elem = Element("thumb")
        thumb_elem.text = avatar_url
        tvshow.append(thumb_elem)

    if banner_url:
        fanart_elem = Element("fanart")
        fanart_thumb_elem = Element("thumb")
        fanart_thumb_elem.text = banner_url
        fanart_elem.append(fanart_thumb_elem)
        tvshow.append(fanart_elem)

    tree = ElementTree(tvshow)
    tree.write(nfo_path, encoding="utf-8", xml_declaration=True)


