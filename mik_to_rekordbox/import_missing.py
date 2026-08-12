"""Import MIK tracks into Rekordbox when they are not already in the library."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from .paths import normalize_path

if TYPE_CHECKING:
    from pyrekordbox import RekordboxXml
    from pyrekordbox.db6.database import Rekordbox6Database

    from .mik_reader import MikTrackMeta


def _file_importable(path: str) -> bool:
    return bool(path) and os.path.isfile(path)


def _title_from_meta(path: str, meta: MikTrackMeta | None) -> str:
    if meta and meta.title:
        return meta.title
    return Path(path).stem


def _get_or_add_artist(db: Rekordbox6Database, name: str):
    artist = db.get_artist(Name=name).one_or_none()
    if artist is None:
        artist = db.add_artist(name=name)
    return artist


def _get_or_add_album(db: Rekordbox6Database, name: str, artist=None):
    album = db.get_album(Name=name).one_or_none()
    if album is None:
        album = db.add_album(name=name, artist=artist)
    return album


def import_track_to_db(
    db: Rekordbox6Database,
    path: str,
    location_index: dict[str, int],
    meta: MikTrackMeta | None = None,
) -> int | None:
    """Add *path* to master.db if the file exists. Updates *location_index*."""
    if not _file_importable(path):
        return None
    norm = normalize_path(path)
    if norm in location_index:
        return location_index[norm]

    kwargs: dict = {"Title": _title_from_meta(path, meta)}
    if meta:
        if meta.bpm is not None:
            kwargs["BPM"] = float(meta.bpm)
        if meta.bitrate is not None:
            kwargs["BitRate"] = int(meta.bitrate)
        if meta.sample_rate is not None:
            kwargs["SampleRate"] = float(meta.sample_rate)

    try:
        content = db.add_content(path, **kwargs)
    except ValueError:
        content = None

    if content is None:
        for existing in db.get_content():
            folder = getattr(existing, "FolderPath", None) or ""
            if not folder:
                continue
            if normalize_path(folder) == norm or folder == path:
                cid = int(existing.ID)
                location_index[norm] = cid
                return cid
        return None

    artist = None
    if meta and meta.artist:
        try:
            artist = _get_or_add_artist(db, meta.artist)
            content.ArtistID = artist.ID
        except Exception:
            artist = None
    if meta and meta.album:
        try:
            album = _get_or_add_album(db, meta.album, artist=artist)
            content.AlbumID = album.ID
        except Exception:
            pass

    db.flush()
    cid = int(content.ID)
    location_index[norm] = cid
    return cid


def import_track_to_xml(
    xml: RekordboxXml,
    path: str,
    location_index: dict[str, int],
    meta: MikTrackMeta | None = None,
) -> int | None:
    """Add *path* to the XML collection if the file exists. Updates *location_index*."""
    if not _file_importable(path):
        return None
    norm = normalize_path(path)
    if norm in location_index:
        return location_index[norm]

    path_obj = Path(path)
    track_kwargs: dict = {"Name": _title_from_meta(path, meta)}
    if meta:
        if meta.artist:
            track_kwargs["Artist"] = meta.artist
        if meta.album:
            track_kwargs["Album"] = meta.album
        if meta.genre:
            track_kwargs["Genre"] = meta.genre
        if meta.bpm is not None:
            track_kwargs["AverageBpm"] = float(meta.bpm)
        if meta.bitrate is not None:
            track_kwargs["BitRate"] = int(meta.bitrate)
        if meta.sample_rate is not None:
            track_kwargs["SampleRate"] = float(meta.sample_rate)
        if meta.key:
            track_kwargs["Tonality"] = meta.key

    try:
        track = xml.add_track(path_obj, **track_kwargs)
    except Exception:
        from .paths import decode_rekordbox_location

        for existing in xml.get_tracks():
            location = existing.get("Location")
            if not location:
                continue
            if normalize_path(decode_rekordbox_location(location)) == norm:
                tid = int(existing["TrackID"])
                location_index[norm] = tid
                return tid
        return None

    tid = int(track["TrackID"])
    location_index[norm] = tid
    return tid
