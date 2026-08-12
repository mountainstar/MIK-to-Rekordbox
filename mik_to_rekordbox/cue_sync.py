"""Copy Mixed In Key energy cue points into Rekordbox (memory cues)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from pyrekordbox.db6 import tables

from .mik_reader import MikCue

if TYPE_CHECKING:
    from pyrekordbox.db6.database import Rekordbox6Database

# Memory cue (same style as MIK → Export Cue Points → Rekordbox).
MEMORY_CUE_KIND = 0
# Rekordbox stores cue frame times at 150 frames/second for these markers.
FRAMES_PER_SEC = 150


@dataclass
class CueSyncResult:
    path: str
    cues_written: int
    skipped_existing: bool = False


def _has_memory_cues(db: Rekordbox6Database, content_id: int | str) -> bool:
    for cue in db.get_cue(ContentID=str(content_id)):
        if int(getattr(cue, "Kind", -1) or 0) == MEMORY_CUE_KIND:
            return True
        # Some exports use Kind None/0 only; also treat Energy comments as present.
        comment = getattr(cue, "Comment", None) or ""
        if str(comment).startswith("Energy"):
            return True
    return False


def _msec_and_frame(time_sec: float) -> tuple[int, int]:
    msec = max(0, int(round(time_sec * 1000)))
    frame = int(msec * FRAMES_PER_SEC // 1000)
    return msec, frame


def write_mik_cues_to_content(
    db: Rekordbox6Database,
    content,
    cues: list[MikCue],
    *,
    only_if_empty: bool = True,
) -> CueSyncResult:
    """Write MIK cues as Rekordbox memory cues on *content*."""
    path = getattr(content, "FolderPath", None) or ""
    if not cues:
        return CueSyncResult(path=path, cues_written=0)

    content_id = content.ID
    if only_if_empty and _has_memory_cues(db, content_id):
        return CueSyncResult(path=path, cues_written=0, skipped_existing=True)

    content_uuid = getattr(content, "UUID", None) or str(uuid4())
    now = datetime.datetime.now()
    written = 0

    for cue in sorted(cues, key=lambda c: c.time_sec):
        msec, frame = _msec_and_frame(cue.time_sec)
        energy = cue.energy_level
        comment = f"Energy {energy}" if energy is not None else (cue.name or "MIK Cue")
        cue_id = db.generate_unused_id(tables.DjmdCue)
        row = tables.DjmdCue.create(
            ID=cue_id,
            ContentID=str(content_id),
            InMsec=msec,
            InFrame=frame,
            InMpegFrame=0,
            InMpegAbs=0,
            OutMsec=-1,
            OutFrame=0,
            OutMpegFrame=0,
            OutMpegAbs=0,
            Kind=MEMORY_CUE_KIND,
            Color=255,
            ColorTableIndex=0,
            ActiveLoop=0,
            Comment=comment,
            BeatLoopSize=0,
            CueMicrosec=0,
            ContentUUID=content_uuid,
            UUID=str(uuid4()),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        written += 1

    if written:
        db.flush()
    return CueSyncResult(path=path, cues_written=written)


def sync_cues_for_tracks(
    db: Rekordbox6Database,
    resolved: list[tuple[str, int]],
    cues_by_path: dict[str, list[MikCue]],
    *,
    only_if_empty: bool = True,
) -> list[CueSyncResult]:
    """Sync MIK cues onto matched Rekordbox content IDs."""
    results: list[CueSyncResult] = []
    for path, content_id in resolved:
        cues = cues_by_path.get(path) or []
        if not cues:
            continue
        content = db.get_content(ID=content_id)
        results.append(
            write_mik_cues_to_content(
                db,
                content,
                cues,
                only_if_empty=only_if_empty,
            )
        )
    return results
