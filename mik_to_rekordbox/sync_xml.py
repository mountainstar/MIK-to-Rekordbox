"""Sync MIK playlists into a Rekordbox XML export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyrekordbox import RekordboxXml

from .matching import build_location_index_from_xml, match_paths
from .mik_reader import MikPlaylistTracks

DEFAULT_XML = Path.home() / "Documents/rekordbox/rekordbox.xml"
MIK_SYNC_FOLDER = "MIK Sync"


@dataclass
class XmlSyncReport:
    playlist_name: str
    matched: int
    missing: list[str]
    basename_matches: list[tuple[str, str]]
    created_playlist: bool
    output_path: Path


def _find_playlist_node(parent, name: str):
    """Find a direct child playlist/folder by name (not deep search)."""
    for child in parent.get_playlists():
        if child.name == name:
            return child
    return None


def _clear_playlist(node) -> None:
    if not node.is_playlist:
        return
    for key in list(node.get_tracks()):
        node.remove_track(key)


def _ensure_folder(xml: RekordboxXml, folder_name: str):
    root = xml.get_playlist()
    folder = _find_playlist_node(root, folder_name)
    if folder is None:
        folder = xml.add_playlist_folder(folder_name)
    return folder


def sync_playlist_to_xml(
    tracks: MikPlaylistTracks,
    *,
    xml_path: Path | str = DEFAULT_XML,
    parent_folder: str | None = MIK_SYNC_FOLDER,
    replace_existing: bool = True,
    allow_basename_fallback: bool = False,
    output_path: Path | str | None = None,
) -> XmlSyncReport:
    """Write or update a Rekordbox XML playlist from MIK track order."""
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(
            f"Rekordbox XML not found at {xml_path}. "
            "In Rekordbox use File → Export Collection in XML format first."
        )

    xml = RekordboxXml(str(xml_path))
    location_index = build_location_index_from_xml(xml)
    match = match_paths(
        tracks.paths,
        location_index,
        allow_basename_fallback=allow_basename_fallback,
    )

    root = xml.get_playlist()
    parent = root
    if parent_folder:
        parent = _ensure_folder(xml, parent_folder)

    playlist_name = tracks.playlist.name
    node = _find_playlist_node(parent, playlist_name)
    created = False
    if node is None:
        node = parent.add_playlist(playlist_name, keytype="TrackID")
        created = True
    elif replace_existing:
        _clear_playlist(node)

    for track_id in match.track_ids:
        node.add_track(track_id)

    destination = Path(output_path) if output_path else xml_path
    xml.save(str(destination))

    return XmlSyncReport(
        playlist_name=playlist_name,
        matched=len(match.track_ids),
        missing=match.missing_paths,
        basename_matches=match.basename_matches,
        created_playlist=created,
        output_path=destination,
    )


def build_path_index_for_debug(xml_path: Path | str) -> dict[str, int]:
    xml = RekordboxXml(str(xml_path))
    return build_location_index_from_xml(xml)
