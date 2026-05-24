"""Read playlists and track order from Mixed In Key's Collection database."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .paths import extract_mik_path
from .platform_paths import DEFAULT_MIK_DB


@dataclass(frozen=True)
class MikPlaylist:
    id: int
    name: str
    is_folder: bool
    parent_id: int | None
    emoji: str | None


@dataclass(frozen=True)
class MikPlaylistTracks:
    playlist: MikPlaylist
    paths: list[str]


class MikReader:
    def __init__(self, db_path: Path | str = DEFAULT_MIK_DB) -> None:
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Mixed In Key database not found: {self.db_path}")

    def _connect(self) -> sqlite3.Connection:
        # MIK keeps Collection11.mikdb open (WAL). busy_timeout waits on its lock;
        # read_uncommitted helps see playlist edits before MIK finishes a checkpoint.
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            timeout=5.0,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA read_uncommitted = 1")
        return conn

    def list_playlists(self, *, include_folders: bool = False) -> list[MikPlaylist]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT Z_PK, ZNAME, ZISFOLDER, ZPARENTCOLLECTION, ZEMOJI
                FROM ZCOLLECTION
                ORDER BY ZISFOLDER DESC, ZNAME COLLATE NOCASE
                """
            ).fetchall()
        playlists: list[MikPlaylist] = []
        for row in rows:
            if row["Z_PK"] == 1:
                continue
            is_folder = bool(row["ZISFOLDER"])
            if is_folder and not include_folders:
                continue
            playlists.append(
                MikPlaylist(
                    id=row["Z_PK"],
                    name=row["ZNAME"] or "",
                    is_folder=is_folder,
                    parent_id=row["ZPARENTCOLLECTION"],
                    emoji=row["ZEMOJI"],
                )
            )
        return playlists

    def get_playlist_by_name(self, name: str) -> MikPlaylist | None:
        target = name.casefold()
        for playlist in self.list_playlists(include_folders=True):
            if playlist.name.casefold() == target:
                return playlist
        return None

    def get_playlist_tracks(self, playlist: MikPlaylist | str) -> MikPlaylistTracks:
        if isinstance(playlist, str):
            found = self.get_playlist_by_name(playlist)
            if found is None:
                raise ValueError(f"MIK playlist not found: {playlist!r}")
            if found.is_folder:
                raise ValueError(f"{playlist!r} is a folder, not a playlist")
            playlist = found
        if playlist.is_folder:
            raise ValueError(f"{playlist.name!r} is a folder, not a playlist")

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT s.ZBOOKMARKDATA
                FROM Z_1SONGS j
                JOIN ZSONG s ON j.Z_5SONGS = s.Z_PK
                WHERE j.Z_1COLLECTIONS = ?
                ORDER BY j.Z_FOK_5SONGS
                """,
                (playlist.id,),
            ).fetchall()

        paths: list[str] = []
        for row in rows:
            path = extract_mik_path(row["ZBOOKMARKDATA"])
            if path:
                paths.append(path)

        return MikPlaylistTracks(playlist=playlist, paths=paths)
