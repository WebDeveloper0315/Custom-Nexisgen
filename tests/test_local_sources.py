import json
from pathlib import Path

from nexis.miner.youtube_1 import read_local_sources, read_sources, resolve_local_source


def test_resolve_local_source_relative(tmp_path: Path) -> None:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    resolved = resolve_local_source("clip.mp4", base_dir=tmp_path)
    assert resolved == video.resolve()


def test_read_sources_mixed(tmp_path: Path) -> None:
    video = tmp_path / "a.mp4"
    video.write_bytes(b"fake")
    sources = tmp_path / "sources.txt"
    sources.write_text(
        json.dumps(
            {
                "files": ["a.mp4"],
                "routes": ["https://example.com/watch?v=abc"],
            }
        ),
        encoding="utf-8",
    )
    file_entries, route_entries = read_sources(sources)
    assert file_entries == [str(video.resolve())]
    assert route_entries == ["https://example.com/watch?v=abc"]


def test_read_local_sources_skips_urls(tmp_path: Path) -> None:
    video = tmp_path / "a.mp4"
    video.write_bytes(b"fake")
    sources = tmp_path / "sources.txt"
    sources.write_text(
        json.dumps(
            {
                "files": ["a.mp4"],
                "routes": ["https://youtube.com/watch?v=abc"],
            }
        ),
        encoding="utf-8",
    )
    entries = read_local_sources(sources_file=sources, sources_dir=tmp_path)
    assert entries == [str(video.resolve())]


def test_read_sources_extra_dir(tmp_path: Path) -> None:
    sub = tmp_path / "videos"
    sub.mkdir()
    (sub / "one.mp4").write_bytes(b"1")
    (sub / "two.mkv").write_bytes(b"2")
    (sub / "readme.txt").write_text("skip", encoding="utf-8")
    sources = tmp_path / "sources.txt"
    sources.write_text(json.dumps({"files": [], "routes": []}), encoding="utf-8")
    file_entries, route_entries = read_sources(sources, extra_dir=sub)
    assert route_entries == []
    assert len(file_entries) == 2
    assert all(e.endswith((".mp4", ".mkv")) for e in file_entries)


def test_read_sources_legacy_txt(tmp_path: Path) -> None:
    video = tmp_path / "a.mp4"
    video.write_bytes(b"fake")
    sources = tmp_path / "sources.txt"
    sources.write_text(
        "a.mp4\nhttps://example.com/watch?v=abc\n# comment\n\n",
        encoding="utf-8",
    )
    file_entries, route_entries = read_sources(sources)
    assert file_entries == [str(video.resolve())]
    assert route_entries == ["https://example.com/watch?v=abc"]
