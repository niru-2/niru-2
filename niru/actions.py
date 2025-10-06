from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Optional

try:
    import yt_dlp  # type: ignore
except Exception:  # pragma: no cover
    yt_dlp = None  # lazy error at runtime


@dataclass
class ActionResult:
    ok: bool
    message: str


def _normalize_path(path: str) -> Path:
    expanded = os.path.expanduser(path)
    absolute = os.path.abspath(expanded)
    return Path(absolute)


def open_folder(path: str, dry_run: bool = False) -> ActionResult:
    if not path:
        return ActionResult(False, "No folder path provided.")

    target = _normalize_path(path)
    if not target.exists():
        return ActionResult(False, f"Folder not found: {target}")
    if not target.is_dir():
        return ActionResult(False, f"Not a folder: {target}")

    if dry_run:
        return ActionResult(True, f"Would open folder: {target}")

    opener = (
        shutil.which("xdg-open")
        or shutil.which("gio")
        or shutil.which("gnome-open")
        or shutil.which("kde-open5")
        or shutil.which("kde-open")
    )

    if not opener:
        return ActionResult(False, "No system opener found (xdg-open/gio/gnome-open).")

    try:
        if os.path.basename(opener) == "gio":
            cmd = [opener, "open", str(target)]
        else:
            cmd = [opener, str(target)]
        subprocess.run(cmd, check=False)
        return ActionResult(True, f"Opened folder: {target}")
    except Exception as exc:
        return ActionResult(False, f"Failed to open folder: {exc}")


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def download_song(query: str, dest_dir: Optional[str] = None, dry_run: bool = False) -> ActionResult:
    if not query:
        return ActionResult(False, "No song query provided.")

    if dest_dir:
        dest_path = _normalize_path(dest_dir)
    else:
        # Default to ~/Music if it exists, else ~/Downloads
        default_music = Path.home() / "Music"
        dest_path = default_music if default_music.exists() else (Path.home() / "Downloads")

    if dry_run:
        return ActionResult(True, f"Would download '{query}' to {dest_path}")

    if yt_dlp is None:
        return ActionResult(False, "yt-dlp is not installed. Install the package dependency.")

    dest_path.mkdir(parents=True, exist_ok=True)

    # Prefer mp3 via ffmpeg if available; otherwise keep bestaudio container
    postprocessors = []
    if _ffmpeg_available():
        postprocessors = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {
                "key": "FFmpegMetadata",
            },
        ]

    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "outtmpl": str(dest_path / "%(title)s.%(ext)s"),
        "quiet": True,
        "restrictfilenames": True,
        "nocheckcertificate": True,
        "postprocessors": postprocessors,
        # Retry a couple times for transient failures
        "retries": 2,
        # Use search if URL was not provided
        # Users can pass full URLs too; ytsearch will handle non-URLs fine
    }

    # If the query looks like a URL, use directly; else use ytsearch1:
    if re.match(r"^https?://", query):
        url = query
    else:
        url = f"ytsearch1:{query}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        title = info.get("title") if isinstance(info, dict) else None
        return ActionResult(True, f"Downloaded: {title or query} -> {dest_path}")
    except Exception as exc:
        # Retry without postprocessing if ffmpeg was the issue
        if postprocessors:
            try:
                ydl_opts_no_pp = dict(ydl_opts)
                ydl_opts_no_pp.pop("postprocessors", None)
                with yt_dlp.YoutubeDL(ydl_opts_no_pp) as ydl:
                    info = ydl.extract_info(url, download=True)
                title = info.get("title") if isinstance(info, dict) else None
                return ActionResult(True, f"Downloaded (no conversion): {title or query} -> {dest_path}")
            except Exception as exc2:
                return ActionResult(False, f"Download failed: {exc2}")
        return ActionResult(False, f"Download failed: {exc}")
