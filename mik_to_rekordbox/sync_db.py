"""Sync MIK playlists directly into Rekordbox master.db (Rekordbox must be closed)."""

from __future__ import annotations

import datetime
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass, field

from pyrekordbox.db6 import tables

from .matching import _is_deleted_content, build_location_index_from_db, match_paths
from .paths import is_rekordbox_internal_path
from .mik_reader import MikPlaylistTracks

MIK_SYNC_FOLDER = "MIK Sync"


@contextmanager
def _suppress_pyrekordbox_playlist_xml_warnings():
    """Hide pre-existing masterPlaylists6.xml drift warnings on commit."""
    logger = logging.getLogger("pyrekordbox.db6.database")
    previous = logger.level
    logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        logger.setLevel(previous)


@dataclass
class DbSyncReport:
    playlist_name: str
    matched: int
    missing: list[str]
    basename_matches: list[tuple[str, str]]
    created_playlist: bool
    playlist_id: str
    tracks_in_db: int = 0
    restored_hidden: list[str] = field(default_factory=list)


def _get_or_create_folder(db, name: str):
    folder = db.get_playlist(Name=name).first()
    if folder is not None and folder.Attribute == 1:
        return folder
    return db.create_playlist_folder(name)


def _find_playlist(db, name: str, parent_id: str | None = None):
    query = db.get_playlist(Name=name)
    for playlist in query:
        if playlist.Attribute != 0:
            continue
        if parent_id is None or str(playlist.ParentID) == str(parent_id):
            return playlist
    return None


def _ensure_playlist_in_xml(db, playlist) -> None:
    """Register playlist nodes Rekordbox expects in masterPlaylists6.xml."""
    if db.playlist_xml is None:
        return
    if db.playlist_xml.get(playlist.ID) is not None:
        return
    db.playlist_xml.add(
        playlist.ID,
        playlist.ParentID,
        int(playlist.Attribute),
        playlist.updated_at,
    )


def _clear_playlist(db, playlist) -> None:
    # Avoid remove_from_playlist: it commits after every track and can confuse Rekordbox.
    songs = (
        db.query(tables.DjmdSongPlaylist)
        .filter_by(PlaylistID=str(playlist.ID))
        .all()
    )
    for song in songs:
        db.delete(song)
    if songs:
        db.flush()


def _refresh_playlist(db, playlist):
    return db.get_playlist(ID=playlist.ID)


def _restore_hidden_content(db, content, mik_path: str) -> bool:
    """Unhide Rekordbox content marked missing when the audio file is still on disk."""
    if not _is_deleted_content(content):
        return False
    folder = getattr(content, "FolderPath", None) or ""
    check_paths = [folder, mik_path]
    if not any(
        p and not is_rekordbox_internal_path(p) and os.path.exists(p) for p in check_paths
    ):
        return False
    content.rb_local_deleted = 0
    content.updated_at = datetime.datetime.now()
    return True


def sync_playlist_to_db(
    tracks: MikPlaylistTracks,
    *,
    db=None,
    parent_folder: str | None = MIK_SYNC_FOLDER,
    replace_existing: bool = True,
    allow_basename_fallback: bool = False,
    restore_hidden: bool = True,
    commit: bool = True,
) -> DbSyncReport:
    """Create or replace a Rekordbox playlist from MIK track order."""
    if db is None:
        from pyrekordbox import Rekordbox6Database

        db = Rekordbox6Database()

    location_index = build_location_index_from_db(db)
    match = match_paths(
        tracks.paths,
        location_index,
        allow_basename_fallback=allow_basename_fallback,
        db=db,
    )

    parent = None
    parent_id = "root"
    if parent_folder:
        parent = _get_or_create_folder(db, parent_folder)
        parent_id = str(parent.ID)
        _ensure_playlist_in_xml(db, parent)

    playlist_name = tracks.playlist.name
    playlist = _find_playlist(db, playlist_name, parent_id=parent_id)
    created = False
    if playlist is None:
        playlist = db.create_playlist(playlist_name, parent=parent)
        created = True
    elif replace_existing:
        _clear_playlist(db, playlist)

    playlist = _refresh_playlist(db, playlist)
    now = datetime.datetime.now()
    playlist.updated_at = now

    restored_hidden: list[str] = []
    for mik_path, content_id in zip(tracks.paths, match.track_ids):
        content = db.get_content(ID=content_id)
        if restore_hidden and _restore_hidden_content(db, content, mik_path):
            restored_hidden.append(mik_path)
        db.add_to_playlist(playlist, content)

    _ensure_playlist_in_xml(db, playlist)
    db.flush()
    playlist = _refresh_playlist(db, playlist)
    tracks_in_db = len(list(playlist.Songs))

    if commit:
        with _suppress_pyrekordbox_playlist_xml_warnings():
            db.commit()

    return DbSyncReport(
        playlist_name=playlist_name,
        matched=len(match.track_ids),
        missing=match.missing_paths,
        basename_matches=match.basename_matches,
        created_playlist=created,
        playlist_id=str(playlist.ID),
        tracks_in_db=tracks_in_db,
        restored_hidden=restored_hidden,
    )
