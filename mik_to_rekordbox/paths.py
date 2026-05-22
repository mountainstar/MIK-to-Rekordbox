"""Path normalization for matching MIK files to Rekordbox entries."""

from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote


def extract_mik_path(bookmark: bytes | None) -> str | None:
    """Extract a filesystem path from a macOS bookmark blob stored in MIK."""
    if not bookmark:
        return None
    text = bookmark.decode("utf-8", errors="ignore")
    candidates = re.findall(r"(/[^\x00-\x1f]{5,})", text)
    if not candidates:
        return None
    audio = [
        p
        for p in candidates
        if re.search(r"\.(mp3|m4a|aiff|aif|wav|flac|alac|ogg)/?$", p, re.I)
    ]
    chosen = audio[-1] if audio else candidates[-1]
    return normalize_path(chosen)


def normalize_path(path: str | Path) -> str:
    """Normalize paths for stable comparison on macOS."""
    cleaned = str(path).rstrip("/")
    return os.path.normcase(os.path.normpath(cleaned))


def decode_rekordbox_location(location: str) -> str:
    """Decode a Rekordbox XML Location attribute to a local path."""
    value = unquote(location)
    if value.startswith("file://localhost/"):
        value = "/" + value[len("file://localhost/") :]
    elif value.startswith("file://localhost"):
        value = "/" + value[len("file://localhost") :].lstrip("/")
    elif value.startswith("file:///"):
        value = value[len("file://") :]
    elif not value.startswith("/") and not value.startswith("."):
        # pyrekordbox and some Rekordbox exports omit the leading slash on macOS
        value = "/" + value
    return normalize_path(value)


def basename_key(path: str | Path) -> str:
    return os.path.basename(normalize_path(path)).casefold()
