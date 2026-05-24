"""Path parsing helpers."""

from mik_to_rekordbox.paths import (
    decode_rekordbox_location,
    extract_mik_path,
    normalize_path,
)


def test_extract_windows_path_from_blob() -> None:
    blob = b"prefix C:\\Music\\Sets\\track.mp3 suffix"
    assert extract_mik_path(blob) == normalize_path(r"C:\Music\Sets\track.mp3")


def test_extract_unix_path_from_blob() -> None:
    blob = b"bookmark /Users/dj/Music/track.flac end"
    assert extract_mik_path(blob) == normalize_path("/Users/dj/Music/track.flac")


def test_decode_file_url_windows() -> None:
    loc = "file:///C:/Users/dj/Music/track.mp3"
    assert decode_rekordbox_location(loc) == normalize_path("C:/Users/dj/Music/track.mp3")
