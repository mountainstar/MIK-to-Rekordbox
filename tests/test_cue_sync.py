"""Tests for MIK → Rekordbox cue sync helpers."""

from mik_to_rekordbox.cue_sync import _msec_and_frame


def test_msec_and_frame() -> None:
    msec, frame = _msec_and_frame(38.106)
    assert msec == 38106
    assert frame == msec * 150 // 1000

    msec, frame = _msec_and_frame(0.0)
    assert msec == 0
    assert frame == 0
