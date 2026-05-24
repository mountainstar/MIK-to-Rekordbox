"""Path normalization for matching MIK files to Rekordbox entries."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

_AUDIO_EXT = re.compile(r"\.(mp3|m4a|aiff|aif|wav|flac|alac|ogg|wma)/?$", re.I)
_UNIX_PATH = re.compile(
    r"(/(?:[^/\x00-\x1f]+/)*[^/\x00-\x1f]+\.(?:mp3|m4a|aiff|aif|wav|flac|alac|ogg|wma))",
    re.I,
)
_WIN_PATH = re.compile(
    r"([A-Za-z]:[\\/](?:[^\\/\x00-\x1f]+[\\/])*[^\\/\x00-\x1f]+\.(?:mp3|m4a|aiff|aif|wav|flac|alac|ogg|wma))",
    re.I,
)
_FILE_URL = re.compile(r"file://[^\s\x00]+", re.I)


def extract_mik_path(bookmark: bytes | None) -> str | None:
    """Extract a filesystem path from a MIK bookmark blob (macOS or Windows)."""
    if not bookmark:
        return None
    text = bookmark.decode("utf-8", errors="ignore")

    candidates: list[str] = []
    candidates.extend(_UNIX_PATH.findall(text))
    candidates.extend(_WIN_PATH.findall(text))
    for match in _FILE_URL.finditer(text):
        decoded = decode_rekordbox_location(match.group(0))
        if decoded:
            candidates.append(decoded)

    if not candidates:
        return None

    audio = [p for p in candidates if _AUDIO_EXT.search(p)]
    chosen = audio[-1] if audio else candidates[-1]
    return normalize_path(chosen)


def normalize_path(path: str | Path) -> str:
    """Normalize paths for stable comparison across platforms."""
    cleaned = str(path).strip().rstrip("/\\")
    if not cleaned:
        return cleaned
    return os.path.normcase(os.path.normpath(cleaned))


def decode_rekordbox_location(location: str) -> str:
    """Decode a Rekordbox XML Location attribute to a local path."""
    value = unquote(location)
    if value.startswith("file://localhost/"):
        value = value[len("file://localhost/") :]
    elif value.startswith("file://localhost"):
        value = value[len("file://localhost") :].lstrip("/")
    elif value.startswith("file:///"):
        value = value[len("file://") :]
        # file:///C:/Music/track.mp3 → C:/Music/track.mp3
        if len(value) >= 3 and value[0] == "/" and value[2] == ":":
            value = value[1:]
    elif value.startswith("file://"):
        value = value[len("file://") :]
    elif (
        sys.platform == "darwin"
        and not value.startswith("/")
        and not re.match(r"[A-Za-z]:", value)
        and not value.startswith(".")
    ):
        # pyrekordbox and some Rekordbox exports omit the leading slash on macOS
        value = "/" + value
    return normalize_path(value)


def is_rekordbox_internal_path(path: str) -> bool:
    """True for Rekordbox content paths that are not real filesystem locations."""
    if not path:
        return True
    lowered = path.replace("\\", "/").casefold()
    return lowered.startswith("/contents") or lowered.startswith("contents/")


def basename_key(path: str | Path) -> str:
    return os.path.basename(normalize_path(path)).casefold()
