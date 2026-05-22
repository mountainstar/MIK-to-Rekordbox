"""Sync MIK playlists into a Rekordbox XML export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pyrekordbox import RekordboxXml

from .matching import build_location_index_from_xml, match_paths
from .mik_reader import MikPlaylistTracks, MikReader

DEFAULT_XML = Path.home() / "Documents/rekordbox/rekordbox.xml"
DEFAULT_OUTPUT_XML = Path.home() / "Documents/rekordbox/rekordbox_mik_sync.xml"
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


def _clear_root_children(root) -> None:
    for child in list(root.get_playlists()):
        root.remove_playlist(child.name)


def _write_playlist_to_folder(
    folder,
    tracks: MikPlaylistTracks,
    location_index: dict[str, int],
    *,
    allow_basename_fallback: bool,
    replace_existing: bool,
) -> XmlSyncReport:
    match = match_paths(
        tracks.paths,
        location_index,
        allow_basename_fallback=allow_basename_fallback,
    )

    playlist_name = tracks.playlist.name
    node = _find_playlist_node(folder, playlist_name)
    created = False
    if node is None:
        node = folder.add_playlist(playlist_name, keytype="TrackID")
        created = True
    elif replace_existing:
        _clear_playlist(node)

    for track_id in match.track_ids:
        node.add_track(track_id)

    return XmlSyncReport(
        playlist_name=playlist_name,
        matched=len(match.track_ids),
        missing=match.missing_paths,
        basename_matches=match.basename_matches,
        created_playlist=created,
        output_path=Path(),  # filled in by caller
    )


def _iter_mik_playlist_tracks(reader: MikReader):
    for pl in reader.list_playlists():
        if pl.is_folder:
            continue
        yield reader.get_playlist_tracks(pl)


def _rebuild_mik_sync_xml(
    source_xml: RekordboxXml,
    *,
    reader: MikReader,
    parent_folder: str,
    replace_existing: bool,
    allow_basename_fallback: bool,
    highlight_name: str | None = None,
) -> XmlSyncReport:
    """Rebuild the MIK Sync folder from all current MIK playlists.

    Uses the collection from the latest Rekordbox export (source_xml) and writes
    only the MIK Sync folder to the output file so deleted playlists disappear.
    """
    location_index = build_location_index_from_xml(source_xml)
    root = source_xml.get_playlist()
    _clear_root_children(root)
    folder = _ensure_folder(source_xml, parent_folder)

    highlight: XmlSyncReport | None = None
    for tracks in _iter_mik_playlist_tracks(reader):
        report = _write_playlist_to_folder(
            folder,
            tracks,
            location_index,
            allow_basename_fallback=allow_basename_fallback,
            replace_existing=replace_existing,
        )
        if highlight_name is None or tracks.playlist.name == highlight_name:
            highlight = report

    if highlight is None:
        raise ValueError(f"MIK playlist not found: {highlight_name!r}")
    return highlight


def sync_playlist_to_xml(
    tracks: MikPlaylistTracks,
    *,
    xml_path: Path | str = DEFAULT_XML,
    parent_folder: str | None = MIK_SYNC_FOLDER,
    replace_existing: bool = True,
    allow_basename_fallback: bool = False,
    output_path: Path | str | None = None,
    reader: MikReader | None = None,
) -> XmlSyncReport:
    """Write or update a Rekordbox XML playlist from MIK track order."""
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(
            f"Rekordbox XML not found at {xml_path}. "
            "In Rekordbox use File → Export Collection in XML format first."
        )

    destination = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_XML
    separate_output = destination.resolve() != xml_path.resolve()

    source_xml = RekordboxXml(str(xml_path))
    folder_name = parent_folder or MIK_SYNC_FOLDER

    if separate_output:
        mik_reader = reader or MikReader()
        report = _rebuild_mik_sync_xml(
            source_xml,
            reader=mik_reader,
            parent_folder=folder_name,
            replace_existing=replace_existing,
            allow_basename_fallback=allow_basename_fallback,
            highlight_name=tracks.playlist.name,
        )
        report.output_path = destination
        source_xml.save(str(destination))
        return report

    location_index = build_location_index_from_xml(source_xml)
    root = source_xml.get_playlist()
    parent = root
    if parent_folder:
        parent = _ensure_folder(source_xml, folder_name)

    report = _write_playlist_to_folder(
        parent,
        tracks,
        location_index,
        allow_basename_fallback=allow_basename_fallback,
        replace_existing=replace_existing,
    )
    report.output_path = destination
    source_xml.save(str(destination))
    return report


def sync_playlists_to_xml(
    names: list[str],
    *,
    xml_path: Path | str = DEFAULT_XML,
    parent_folder: str | None = MIK_SYNC_FOLDER,
    replace_existing: bool = True,
    allow_basename_fallback: bool = False,
    output_path: Path | str | None = None,
    reader: MikReader | None = None,
) -> list[XmlSyncReport]:
    """Sync multiple MIK playlists; rebuilds the output XML once when using a separate file."""
    if not names:
        return []

    mik_reader = reader or MikReader()
    xml_path = Path(xml_path)
    destination = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_XML
    separate_output = destination.resolve() != xml_path.resolve()

    if separate_output:
        source_xml = RekordboxXml(str(xml_path))
        location_index = build_location_index_from_xml(source_xml)
        folder_name = parent_folder or MIK_SYNC_FOLDER
        root = source_xml.get_playlist()
        _clear_root_children(root)
        folder = _ensure_folder(source_xml, folder_name)

        wanted = {name.casefold() for name in names}
        reports: list[XmlSyncReport] = []
        for tracks in _iter_mik_playlist_tracks(mik_reader):
            report = _write_playlist_to_folder(
                folder,
                tracks,
                location_index,
                allow_basename_fallback=allow_basename_fallback,
                replace_existing=replace_existing,
            )
            report.output_path = destination
            if tracks.playlist.name.casefold() in wanted:
                reports.append(report)

        source_xml.save(str(destination))
        return reports

    return [
        sync_playlist_to_xml(
            mik_reader.get_playlist_tracks(name),
            xml_path=xml_path,
            parent_folder=parent_folder,
            replace_existing=replace_existing,
            allow_basename_fallback=allow_basename_fallback,
            output_path=output_path,
            reader=mik_reader,
        )
        for name in names
    ]


def build_path_index_for_debug(xml_path: Path | str) -> dict[str, int]:
    xml = RekordboxXml(str(xml_path))
    return build_location_index_from_xml(xml)
