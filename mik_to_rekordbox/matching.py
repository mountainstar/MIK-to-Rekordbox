"""Match MIK file paths to Rekordbox track identifiers."""

from __future__ import annotations

from dataclasses import dataclass, field

from .paths import basename_key, decode_rekordbox_location, normalize_path


@dataclass
class MatchResult:
    track_ids: list[int]
    missing_paths: list[str] = field(default_factory=list)
    basename_matches: list[tuple[str, str]] = field(default_factory=list)


def build_location_index_from_xml(xml) -> dict[str, int]:
    """Map normalized filesystem paths to Rekordbox TrackID from XML collection."""
    index: dict[str, int] = {}
    for track in xml.get_tracks():
        location = track.get("Location")
        if not location:
            continue
        path = normalize_path(decode_rekordbox_location(location))
        index[path] = int(track["TrackID"])
    return index


def _is_deleted_content(content) -> bool:
    return bool(getattr(content, "rb_local_deleted", 0))


def build_location_index_from_db(db) -> dict[str, int]:
    """Map normalized filesystem paths to Rekordbox content IDs.

    When duplicate paths exist, prefer entries Rekordbox still considers active
    (rb_local_deleted=0). Deleted duplicates are common after cloud moves.
    """
    index: dict[str, int] = {}
    index_deleted: dict[str, bool] = {}
    for content in db.get_content():
        folder = getattr(content, "FolderPath", None) or ""
        if not folder:
            continue
        path = normalize_path(folder)
        cid = int(content.ID)
        deleted = _is_deleted_content(content)
        if path not in index:
            index[path] = cid
            index_deleted[path] = deleted
        elif index_deleted[path] and not deleted:
            index[path] = cid
            index_deleted[path] = False
        elif not index_deleted[path] and deleted:
            continue
        else:
            index[path] = cid
    return index


def _best_content_for_basename(db, key: str) -> tuple[int, str] | None:
    """Pick a single content ID for a filename, preferring non-deleted entries."""
    active: list[tuple[str, int]] = []
    deleted: list[tuple[str, int]] = []
    for content in db.get_content():
        folder = getattr(content, "FolderPath", None) or ""
        if not folder or basename_key(folder) != key:
            continue
        entry = (normalize_path(folder), int(content.ID))
        if _is_deleted_content(content):
            deleted.append(entry)
        else:
            active.append(entry)
    pool = active or deleted
    if len(pool) == 1:
        path, cid = pool[0]
        return cid, path
    return None


def match_paths(
    paths: list[str],
    location_index: dict[str, int],
    *,
    allow_basename_fallback: bool = False,
    db=None,
) -> MatchResult:
    """Resolve MIK paths to Rekordbox track/content IDs."""
    basename_index: dict[str, list[str]] = {}
    if allow_basename_fallback:
        for stored in location_index:
            basename_index.setdefault(basename_key(stored), []).append(stored)

    track_ids: list[int] = []
    missing: list[str] = []
    basename_matches: list[tuple[str, str]] = []

    for raw in paths:
        norm = normalize_path(raw)
        track_id = location_index.get(norm)
        if track_id is not None:
            track_ids.append(track_id)
            continue

        if allow_basename_fallback:
            key = basename_key(norm)
            if db is not None:
                resolved = _best_content_for_basename(db, key)
                if resolved is not None:
                    cid, matched = resolved
                    track_ids.append(cid)
                    basename_matches.append((raw, matched))
                    continue
            candidates = basename_index.get(key, [])
            if len(candidates) == 1:
                matched = candidates[0]
                track_ids.append(location_index[matched])
                basename_matches.append((raw, matched))
                continue

        missing.append(raw)

    return MatchResult(
        track_ids=track_ids,
        missing_paths=missing,
        basename_matches=basename_matches,
    )
