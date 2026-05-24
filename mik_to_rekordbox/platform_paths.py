"""Default filesystem locations for MIK and Rekordbox on each OS."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_AUDIO_DB_NAME = "Collection11.mikdb"


def rekordbox_documents_dir() -> Path:
    return Path.home() / "Documents" / "rekordbox"


def default_rekordbox_xml() -> Path:
    return rekordbox_documents_dir() / "rekordbox.xml"


def default_output_xml() -> Path:
    return rekordbox_documents_dir() / "rekordbox_mik_sync.xml"


def mik_db_candidates() -> list[Path]:
    home = Path.home()
    candidates: list[Path] = []

    if sys.platform == "darwin":
        candidates.append(
            home / "Library/Application Support/Mixedinkey" / _AUDIO_DB_NAME
        )
    elif sys.platform == "win32":
        for env in ("LOCALAPPDATA", "APPDATA"):
            base = os.environ.get(env)
            if not base:
                continue
            root = Path(base)
            candidates.extend(
                [
                    root / "Mixedinkey" / _AUDIO_DB_NAME,
                    root / "Mixed In Key" / "Mixed In Key" / _AUDIO_DB_NAME,
                    root / "Mixed In Key" / _AUDIO_DB_NAME,
                ]
            )
    else:
        candidates.append(home / ".local/share/Mixedinkey" / _AUDIO_DB_NAME)

    # De-duplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def default_mik_db() -> Path:
    for path in mik_db_candidates():
        if path.exists():
            return path
    candidates = mik_db_candidates()
    return candidates[0] if candidates else Path(_AUDIO_DB_NAME)


def rekordbox_quit_hint() -> str:
    if sys.platform == "win32":
        return "fully quit Rekordbox (close the app)"
    return "quit Rekordbox (Cmd+Q)"


# Import-time default for argparse / MikReader signatures (same pattern as before).
DEFAULT_MIK_DB = default_mik_db()
