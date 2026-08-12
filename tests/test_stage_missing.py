"""Tests for staging missing files."""

from __future__ import annotations

import tempfile
from pathlib import Path

from mik_to_rekordbox.stage_missing import copy_missing_paths, unique_dest_path


def test_unique_dest_path_collision() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        (dest / "track.mp3").write_bytes(b"a")
        second = unique_dest_path(dest, "track.mp3")
        assert second.name == "track (2).mp3"
        second.write_bytes(b"b")
        third = unique_dest_path(dest, "track.mp3")
        assert third.name == "track (3).mp3"


def test_copy_missing_paths() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        src_dir = root / "src"
        dest_dir = root / "dest"
        src_dir.mkdir()
        existing = src_dir / "a.mp3"
        existing.write_bytes(b"audio")
        missing = str(src_dir / "gone.mp3")

        copied, not_on_disk, errors = copy_missing_paths(
            [str(existing), missing],
            dest_dir,
        )
        assert len(copied) == 1
        assert Path(copied[0][1]).exists()
        assert not_on_disk == [missing]
        assert errors == []
