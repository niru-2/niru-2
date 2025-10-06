from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class Intent:
    name: str
    params: Dict[str, str]


_COMMON_FOLDERS = {
    "downloads": str(Path.home() / "Downloads"),
    "download": str(Path.home() / "Downloads"),
    "docs": str(Path.home() / "Documents"),
    "documents": str(Path.home() / "Documents"),
    "music": str(Path.home() / "Music"),
    "songs": str(Path.home() / "Music"),
    "pictures": str(Path.home() / "Pictures"),
    "photos": str(Path.home() / "Pictures"),
    "desktop": str(Path.home() / "Desktop"),
    "videos": str(Path.home() / "Videos"),
}


_QUOTED_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")


def _extract_first_quoted(text: str) -> Optional[str]:
    match = _QUOTED_PATTERN.search(text)
    return match.group(1).strip() if match else None


def _extract_path(text: str) -> Optional[str]:
    # Prefer quoted path
    quoted = _extract_first_quoted(text)
    if quoted:
        return quoted

    # Look for absolute, relative, or home-based paths
    path_match = re.search(r"(~/[^\s]+|/[^\s]+|\.[^\s]*)", text)
    if path_match:
        return path_match.group(1)

    # Look for named common folders
    for name, folder in _COMMON_FOLDERS.items():
        if re.search(rf"\b{name}\b", text):
            return folder

    # Look for 'to/into/in <folder>' patterns
    to_match = re.search(r"\b(?:to|into|in)\s+([^\n]+)$", text)
    if to_match:
        candidate = to_match.group(1).strip()
        quoted = _extract_first_quoted(candidate)
        if quoted:
            return quoted
        # Fallback: if it's a single word that maps to known folder
        single = candidate.split()[0]
        if single.lower() in _COMMON_FOLDERS:
            return _COMMON_FOLDERS[single.lower()]
        return candidate

    return None


def _extract_song_query(text: str) -> Optional[str]:
    # Prefer quoted query
    quoted = _extract_first_quoted(text)
    if quoted:
        return quoted

    # Strip common filler words
    cleaned = re.sub(r"\b(for me|please|pls|kindly|a|the)\b", " ", text, flags=re.I)

    # Remove leading verbs and nouns associated with this intent
    cleaned = re.sub(r"\b(download|play|get|grab|find|search|song|music|track|audio)\b", " ", cleaned, flags=re.I)

    # Remove destination directive
    cleaned = re.split(r"\b(?:to|into|in)\b", cleaned, maxsplit=1, flags=re.I)[0]

    cleaned = cleaned.strip()
    # If what's left is too short, abort
    if len(cleaned) < 2:
        return None
    return cleaned


def detect_intent(text: str) -> Intent:
    lc = text.lower().strip()

    # Open folder intent
    if re.search(r"\b(open|show|reveal|launch)\b", lc) and re.search(r"\b(folder|directory|dir|explorer|file manager)\b", lc) or re.search(r"\bopen\s+(/|~|\.)", lc):
        path = _extract_path(text)
        return Intent(name="open_folder", params={"path": path or ""})

    # Download song intent
    if re.search(r"\b(download|get|grab)\b", lc) and re.search(r"\b(song|music|track|audio)\b", lc):
        query = _extract_song_query(text) or ""
        dest = _extract_path(text)
        return Intent(name="download_song", params={"query": query, "dest": dest or ""})

    # Fallbacks: simple commands like 'open ~/Downloads'
    if re.match(r"^open\s+", lc):
        path = _extract_path(text)
        return Intent(name="open_folder", params={"path": path or ""})

    return Intent(name="unknown", params={})
