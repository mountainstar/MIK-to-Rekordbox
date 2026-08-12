"""Format sync results for CLI and GUI output."""

from __future__ import annotations

from .platform_paths import rekordbox_quit_hint
from .sync_db import MIK_SYNC_FOLDER


def format_sync_report(report, *, method: str) -> tuple[list[str], int]:
    """Return human-readable lines and an exit code (0 ok, 2 partial miss)."""
    lines = [
        f"Playlist: {report.playlist_name}",
        f"Method:   {method}",
        f"Matched:  {report.matched} tracks",
    ]
    if report.created_playlist:
        lines.append("Created new Rekordbox playlist")
    else:
        lines.append("Updated existing Rekordbox playlist")

    if report.basename_matches:
        lines.append(f"Basename fallback matches: {len(report.basename_matches)}")
        for src, dst in report.basename_matches[:5]:
            lines.append(f"  {src}")
            lines.append(f"    -> {dst}")
        if len(report.basename_matches) > 5:
            lines.append(f"  ... and {len(report.basename_matches) - 5} more")

    imported = getattr(report, "imported_paths", None)
    if imported:
        lines.append(f"Imported into Rekordbox: {len(imported)}")
        for path in imported[:5]:
            lines.append(f"  {path}")
        if len(imported) > 5:
            lines.append(f"  ... and {len(imported) - 5} more")

    cues_written = getattr(report, "cues_written", None)
    if cues_written:
        lines.append(f"MIK cue points written: {cues_written}")
    cues_skipped = getattr(report, "cues_skipped_existing", None)
    if cues_skipped:
        lines.append(f"Tracks already had cues (left unchanged): {cues_skipped}")

    restored = getattr(report, "restored_hidden", None)
    if restored:
        lines.append(f"Restored in library (were marked missing): {len(restored)}")
        for path in restored[:5]:
            lines.append(f"  {path}")
        if len(restored) > 5:
            lines.append(f"  ... and {len(restored) - 5} more")

    code = 0
    if report.missing:
        lines.append(
            f"Still missing ({len(report.missing)}) — not in Rekordbox and file not found or unsupported:"
        )
        for path in report.missing[:10]:
            lines.append(f"  {path}")
        if len(report.missing) > 10:
            lines.append(f"  ... and {len(report.missing) - 10} more")
        code = 2

    if hasattr(report, "output_path"):
        lines.append(f"XML written: {report.output_path}")
        lines.append("")
        lines.append("Next steps in Rekordbox:")
        lines.append("  1. File → Preferences → Advanced → point XML import to the file above")
        lines.append("  2. Click the XML refresh button in the left tree")
        lines.append(f"  3. Open '{MIK_SYNC_FOLDER}' → '{report.playlist_name}'")
        lines.append("  4. Right-click the playlist → Import Playlist")
    else:
        tracks_in_db = getattr(report, "tracks_in_db", None)
        if tracks_in_db is not None:
            lines.append(f"Tracks in database: {tracks_in_db}")
            if tracks_in_db != report.matched:
                lines.append(
                    "Warning: database track count does not match matched count. "
                    "Quit Rekordbox fully and re-run sync."
                )
        lines.append(
            f"Rekordbox database updated. {rekordbox_quit_hint().capitalize()}, reopen it, "
            "then open the playlist under MIK Sync."
        )

    return lines, code


def format_stage_report(report) -> tuple[list[str], int]:
    """Return human-readable lines and an exit code for a StageReport."""
    lines = [
        f"Playlist: {report.playlist_name}",
        f"Staging folder: {report.dest}",
        f"Already in Rekordbox: {report.already_in_rb}",
        f"Copied: {len(report.copied)}",
    ]
    for _src, dst in report.copied[:10]:
        lines.append(f"  → {dst}")
    if len(report.copied) > 10:
        lines.append(f"  ... and {len(report.copied) - 10} more")

    code = 0
    if report.not_on_disk:
        lines.append(f"Not on disk ({len(report.not_on_disk)}):")
        for path in report.not_on_disk[:10]:
            lines.append(f"  {path}")
        if len(report.not_on_disk) > 10:
            lines.append(f"  ... and {len(report.not_on_disk) - 10} more")
        code = 2

    if report.skipped_errors:
        lines.append(f"Copy errors ({len(report.skipped_errors)}):")
        for path, reason in report.skipped_errors[:5]:
            lines.append(f"  {path}: {reason}")
        if len(report.skipped_errors) > 5:
            lines.append(f"  ... and {len(report.skipped_errors) - 5} more")
        code = max(code, 1)

    lines.append("")
    lines.append("Next steps:")
    lines.append(f"  1. Drag {report.dest} into Rekordbox to import the files")
    lines.append("  2. Analyze tracks in Rekordbox if prompted")
    lines.append("  3. Sync the MIK playlist so order is restored under MIK Sync")
    return lines, code
