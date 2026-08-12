"""Copy MIK tracks missing from Rekordbox into a user-chosen staging folder."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from .matching import build_location_index_from_db, build_location_index_from_xml, match_paths
from .mik_reader import MikPlaylistTracks, MikReader

if TYPE_CHECKING:
    from pyrekordbox import RekordboxXml
    from pyrekordbox.db6.database import Rekordbox6Database


@dataclass
class StageReport:
    playlist_name: str
    dest: Path
    copied: list[tuple[str, str]] = field(default_factory=list)
    already_in_rb: int = 0
    not_on_disk: list[str] = field(default_factory=list)
    skipped_errors: list[tuple[str, str]] = field(default_factory=list)


def _safe_playlist_dirname(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return cleaned or "playlist"


def unique_dest_path(dest_dir: Path, filename: str) -> Path:
    """Return dest_dir/filename, or track (2).ext if the name already exists."""
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    n = 2
    while True:
        candidate = dest_dir / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def copy_missing_paths(
    missing_paths: list[str],
    dest_dir: Path,
) -> tuple[list[tuple[str, str]], list[str], list[tuple[str, str]]]:
    """Copy missing source files into dest_dir. Returns (copied, not_on_disk, errors)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[tuple[str, str]] = []
    not_on_disk: list[str] = []
    errors: list[tuple[str, str]] = []

    for src in missing_paths:
        if not src or not os.path.isfile(src):
            not_on_disk.append(src)
            continue
        try:
            target = unique_dest_path(dest_dir, os.path.basename(src))
            shutil.copy2(src, target)
            copied.append((src, str(target)))
        except OSError as exc:
            errors.append((src, str(exc)))

    return copied, not_on_disk, errors


def stage_missing_tracks(
    tracks: MikPlaylistTracks,
    dest: Path | str,
    *,
    location_index: dict[str, int],
    allow_basename_fallback: bool = False,
    db: Rekordbox6Database | None = None,
    xml: RekordboxXml | None = None,
    use_playlist_subdir: bool = False,
) -> StageReport:
    """Copy tracks from a MIK playlist that are not in Rekordbox into *dest*."""
    dest_root = Path(dest)
    match = match_paths(
        tracks.paths,
        location_index,
        allow_basename_fallback=allow_basename_fallback,
        import_missing=False,
        db=db,
        xml=xml,
    )

    playlist_name = tracks.playlist.name
    if use_playlist_subdir:
        dest_dir = dest_root / _safe_playlist_dirname(playlist_name)
    else:
        dest_dir = dest_root

    copied, not_on_disk, errors = copy_missing_paths(match.missing_paths, dest_dir)

    return StageReport(
        playlist_name=playlist_name,
        dest=dest_dir,
        copied=copied,
        already_in_rb=len(match.track_ids),
        not_on_disk=not_on_disk,
        skipped_errors=errors,
    )


def stage_playlists(
    names: list[str],
    dest: Path | str,
    *,
    reader: MikReader | None = None,
    method: str = "db",
    xml_path: Path | str | None = None,
    allow_basename_fallback: bool = False,
) -> list[StageReport]:
    """Stage missing tracks for one or more MIK playlists."""
    mik_reader = reader or MikReader()
    dest_root = Path(dest)
    use_subdir = len(names) > 1

    db = None
    xml = None
    if method == "xml":
        from pyrekordbox import RekordboxXml

        from .sync_xml import DEFAULT_XML

        path = Path(xml_path) if xml_path is not None else DEFAULT_XML
        if not path.exists():
            raise FileNotFoundError(
                f"Rekordbox XML not found at {path}. "
                "Export your collection from Rekordbox first, or use --method db."
            )
        xml = RekordboxXml(str(path))
        location_index = build_location_index_from_xml(xml)
    else:
        from pyrekordbox import Rekordbox6Database

        db = Rekordbox6Database()
        location_index = build_location_index_from_db(db)

    reports: list[StageReport] = []
    for name in names:
        tracks = mik_reader.get_playlist_tracks(name)
        reports.append(
            stage_missing_tracks(
                tracks,
                dest_root,
                location_index=location_index,
                allow_basename_fallback=allow_basename_fallback,
                db=db,
                xml=xml,
                use_playlist_subdir=use_subdir,
            )
        )
    return reports
