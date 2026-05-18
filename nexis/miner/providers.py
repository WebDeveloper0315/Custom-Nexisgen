"""Source provider abstraction for miner ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
import json
from urllib.parse import parse_qs, urlparse

from .youtube_1 import (
    VIDEO_EXTENSIONS,
    create_clip,
    download_source_video,
    extract_first_frame,
    local_source_video_id,
    probe_video,
    read_local_sources,
    read_sources,
    read_json_sources,
    stage_local_source_video,
)


class SourceProvider(Protocol):
    def read_sources(self, path: Path) -> list[str]: ...

    def source_video_id(self, url: str) -> str: ...

    def download(self, url: str, output_dir: Path) -> Path: ...

    def probe(self, path: Path) -> dict[str, Any]: ...

    def create_clip(self, src: Path, dst: Path, start_sec: float) -> None: ...

    def extract_first_frame(self, src: Path, dst: Path) -> None: ...


class GenericSourceProvider:
    """Source provider: local video files or yt-dlp remote URLs."""

    def __init__(self, *, local_sources_dir: Path | None = None) -> None:
        self.local_sources_dir = local_sources_dir

    def read_sources(self, path: Path) -> list[str]:
        return read_sources(path, extra_dir=self.local_sources_dir)

    def read_json_sources(self, path: Path) -> tuple[list[str], list[str]]:
        return read_json_sources(path, extra_dir=self.local_sources_dir)

    def source_video_id(self, url: str) -> str:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host == "youtu.be":
            return parsed.path.strip("/") or url
        if host == "youtube.com" or host.endswith(".youtube.com"):
            query = parse_qs(parsed.query)
            values = query.get("v", [])
            if values and values[0].strip():
                return values[0].strip()
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] in {"shorts", "embed", "v"}:
                return parts[1]
        if host:
            return f"{host}_{parsed.path.strip('/').replace('/', '_') or 'root'}"
        return url

    def download(self, url: str, output_dir: Path) -> Path:
        path = Path(url)
        if path.is_file():
            return stage_local_source_video(path, output_dir)
        return download_source_video(url, output_dir)

    def probe(self, path: Path) -> dict[str, Any]:
        return probe_video(path)

    def create_clip(self, src: Path, dst: Path, start_sec: float) -> None:
        create_clip(src, dst, start_sec)

    def extract_first_frame(self, src: Path, dst: Path) -> None:
        extract_first_frame(src, dst)

    def create_info(self, src: Path, clip_name: str, frame_name: str, frame_path: Path, info_path: Path, start_sec: float, clip_id: str, source_id: str, repo_url: str) -> None:
        info_path.parent.mkdir(parents=True, exist_ok=True)
        info_path.write_text(json.dumps({
            "ClipPath": str(src),
            "ClipName": clip_name,
            "FrameName": frame_name,
            "FramePath": str(frame_path),
            "StartSec": start_sec,
            "ClipID": clip_id,
            "SourceID": source_id,
            "RepoURL": repo_url,
        }, indent=2))


class LocalSourceProvider:
    """Local video files only; never calls yt-dlp."""

    def __init__(self, *, sources_dir: Path, sources_file: Path) -> None:
        self.sources_dir = sources_dir
        self.sources_file = sources_file

    def read_sources(self, path: Path) -> list[str]:
        del path  # uses configured sources_file + sources_dir
        entries = read_local_sources(
            sources_file=self.sources_file,
            sources_dir=self.sources_dir,
        )
        if not entries:
            raise RuntimeError(
                f"no local videos found in {self.sources_dir} "
                f"(supported: {', '.join(sorted(VIDEO_EXTENSIONS))})"
            )
        return entries

    def source_video_id(self, url: str) -> str:
        path = Path(url)
        if not path.is_file():
            raise ValueError(f"expected local file path, got: {url}")
        return local_source_video_id(path)

    def download(self, url: str, output_dir: Path) -> Path:
        path = Path(url)
        if not path.is_file():
            raise ValueError(f"expected local file path, got: {url}")
        return stage_local_source_video(path, output_dir)

    def probe(self, path: Path) -> dict[str, Any]:
        return probe_video(path)

    def create_clip(self, src: Path, dst: Path, start_sec: float) -> None:
        create_clip(src, dst, start_sec)

    def extract_first_frame(self, src: Path, dst: Path) -> None:
        extract_first_frame(src, dst)


# Back-compat alias.
YouTubeSourceProvider = GenericSourceProvider
