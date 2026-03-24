from __future__ import annotations

from datetime import date
from pathlib import Path
from xml.etree.ElementTree import parse as parse_xml

from teletube.nfo import create_nfo_file, create_tvshow_nfo_file


def test_create_nfo_file_structure(tmp_path: Path) -> None:
    create_nfo_file(
        video_dir=tmp_path,
        base_name="2026-03-15 dQw4w9WgXcQ",
        title="Test Video Title",
        upload_date=date(2026, 3, 15),
        video_id="dQw4w9WgXcQ",
    )
    
    nfo_file = tmp_path / "2026-03-15 dQw4w9WgXcQ.nfo"
    assert nfo_file.exists()


def test_create_nfo_file_content(tmp_path: Path) -> None:
    create_nfo_file(
        video_dir=tmp_path,
        base_name="2026-03-15 dQw4w9WgXcQ",
        title="Test Video Title",
        upload_date=date(2026, 3, 15),
        video_id="dQw4w9WgXcQ",
        description="This is the video description from YouTube",
    )
    
    nfo_file = tmp_path / "2026-03-15 dQw4w9WgXcQ.nfo"
    tree = parse_xml(nfo_file)
    root = tree.getroot()
    
    assert root.tag == "episodedetails"
    
    title = root.find("title")
    assert title is not None
    assert title.text == "Test Video Title"

    episode = root.find("episode")
    assert episode is not None
    assert episode.text == "074"  # day-of-year of 2026-03-15

    aired = root.find("aired")
    assert aired is not None
    assert aired.text == "2026-03-15"
    
    plot = root.find("plot")
    assert plot is not None
    assert plot.text == "This is the video description from YouTube"
    
    uniqueid = root.find("uniqueid")
    assert uniqueid is not None
    assert uniqueid.get("type") == "youtube"
    assert uniqueid.text == "dQw4w9WgXcQ"


def test_create_nfo_file_xml_declaration(tmp_path: Path) -> None:
    create_nfo_file(
        video_dir=tmp_path,
        base_name="2026-01-01 test123",
        title="Title",
        upload_date=date(2026, 1, 1),
        video_id="test123",
        description="",
    )
    
    nfo_file = tmp_path / "2026-01-01 test123.nfo"
    content = nfo_file.read_text(encoding="utf-8")
    
    assert content.startswith("<?xml")
    assert "encoding=" in content


def test_create_nfo_file_fallback_empty_description(tmp_path: Path) -> None:
    create_nfo_file(
        video_dir=tmp_path,
        base_name="2026-01-01 test123",
        title="Title",
        upload_date=date(2026, 1, 1),
        video_id="test123",
        description="",
    )
    

    nfo_file = tmp_path / "2026-01-01 test123.nfo"
    tree = parse_xml(nfo_file)
    root = tree.getroot()
    
    plot = root.find("plot")
    assert plot is not None
    # Should fallback to date-based description when empty
    assert plot.text == "YouTube video from 2026-01-01"


def test_create_tvshow_nfo_file_content(tmp_path: Path) -> None:
    create_tvshow_nfo_file(
        channel_dir=tmp_path / "@mychannel",
        title="@mychannel",
        description="Channel bio",
        avatar_url="https://img.example/avatar.jpg",
        banner_url="https://img.example/banner.jpg",
    )

    nfo_file = tmp_path / "@mychannel" / "tvshow.nfo"
    tree = parse_xml(nfo_file)
    root = tree.getroot()

    assert root.tag == "tvshow"
    assert root.findtext("title") == "@mychannel"
    assert root.findtext("plot") == "Channel bio"
    assert root.findtext("thumb") == "https://img.example/avatar.jpg"
    assert root.findtext("fanart/thumb") == "https://img.example/banner.jpg"


def test_create_tvshow_nfo_file_without_optional_metadata(tmp_path: Path) -> None:
    create_tvshow_nfo_file(
        channel_dir=tmp_path / "@mychannel",
        title="@mychannel",
    )

    nfo_file = tmp_path / "@mychannel" / "tvshow.nfo"
    tree = parse_xml(nfo_file)
    root = tree.getroot()

    assert root.tag == "tvshow"
    assert root.findtext("title") == "@mychannel"
    assert root.find("plot") is None
    assert root.find("thumb") is None
    assert root.find("fanart") is None


