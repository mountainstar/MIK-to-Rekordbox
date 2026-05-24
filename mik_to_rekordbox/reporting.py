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

    restored = getattr(report, "restored_hidden", None)
    if restored:
        lines.append(f"Restored in library (were marked missing): {len(restored)}")
        for path in restored[:5]:
            lines.append(f"  {path}")
        if len(restored) > 5:
            lines.append(f"  ... and {len(restored) - 5} more")

    code = 0
    if report.missing:
        lines.append(f"Missing in Rekordbox ({len(report.missing)}):")
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
