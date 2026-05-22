"""Command-line interface for mik-to-rekordbox."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .mik_reader import DEFAULT_MIK_DB, MikReader
from .reporting import format_sync_report
from .sync_db import MIK_SYNC_FOLDER, sync_playlist_to_db
from .sync_xml import DEFAULT_XML, sync_playlist_to_xml, sync_playlists_to_xml

DEFAULT_OUTPUT_XML = Path.home() / "Documents/rekordbox/rekordbox_mik_sync.xml"


def _print_report(report, *, method: str) -> int:
    lines, code = format_sync_report(report, method=method)
    for line in lines:
        print(line)
    return code


def cmd_list(args: argparse.Namespace) -> int:
    reader = MikReader(args.mik_db)
    playlists = reader.list_playlists(include_folders=args.include_folders)
    for pl in playlists:
        prefix = "[folder]" if pl.is_folder else "[playlist]"
        emoji = f" {pl.emoji}" if pl.emoji else ""
        try:
            count = ""
            if not pl.is_folder:
                count = f" ({len(reader.get_playlist_tracks(pl).paths)} tracks)"
        except ValueError:
            count = ""
        print(f"{prefix} {pl.name}{emoji}{count}")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    reader = MikReader(args.mik_db)
    names = args.playlists or []
    if args.all:
        names = [p.name for p in reader.list_playlists() if not p.is_folder]

    if not names:
        print("Specify playlist name(s) or use --all", file=sys.stderr)
        return 1

    exit_code = 0
    if args.dry_run:
        for name in names:
            tracks = reader.get_playlist_tracks(name)
            print(f"{name}: {len(tracks.paths)} tracks in MIK")
    elif args.method == "xml":
        reports = sync_playlists_to_xml(
            names,
            xml_path=args.xml,
            parent_folder=args.parent_folder,
            replace_existing=not args.keep_existing,
            allow_basename_fallback=args.basename_fallback,
            output_path=args.output,
            reader=reader,
        )
        for report in reports:
            code = _print_report(report, method="rekordbox XML")
            exit_code = max(exit_code, code)
            print()
    else:
        for name in names:
            tracks = reader.get_playlist_tracks(name)
            report = sync_playlist_to_db(
                tracks,
                parent_folder=args.parent_folder,
                replace_existing=not args.keep_existing,
                allow_basename_fallback=args.basename_fallback,
                restore_hidden=not args.no_restore_hidden,
                commit=not args.no_commit,
            )
            code = _print_report(report, method="rekordbox database")
            exit_code = max(exit_code, code)
            print()

    if args.dry_run:
        print("Dry run only — no files were modified.")
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mik-sync",
        description="Sync Mixed In Key playlists into Rekordbox.",
    )
    parser.add_argument(
        "--mik-db",
        type=Path,
        default=DEFAULT_MIK_DB,
        help=f"Path to Collection11.mikdb (default: {DEFAULT_MIK_DB})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List playlists in Mixed In Key")
    list_parser.add_argument(
        "--include-folders",
        action="store_true",
        help="Include folder nodes, not just playlists",
    )
    list_parser.set_defaults(func=cmd_list)

    sync_parser = sub.add_parser("sync", help="Sync one or more MIK playlists to Rekordbox")
    sync_parser.add_argument(
        "playlists",
        nargs="*",
        help="MIK playlist name(s), e.g. '05/19/2026'",
    )
    sync_parser.add_argument(
        "--all",
        action="store_true",
        help="Sync every non-folder playlist in MIK",
    )
    sync_parser.add_argument(
        "--method",
        choices=("xml", "db"),
        default="xml",
        help="xml: write Rekordbox XML (default, safest). db: write master.db directly.",
    )
    sync_parser.add_argument(
        "--xml",
        type=Path,
        default=DEFAULT_XML,
        help=f"Source Rekordbox XML export (default: {DEFAULT_XML})",
    )
    sync_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output XML path (default: overwrite --xml, or {DEFAULT_OUTPUT_XML} if unset)",
    )
    sync_parser.add_argument(
        "--parent-folder",
        default=MIK_SYNC_FOLDER,
        help=f"Rekordbox folder for synced playlists (default: {MIK_SYNC_FOLDER!r})",
    )
    sync_parser.add_argument(
        "--no-parent-folder",
        action="store_true",
        help="Place playlists at XML/root level instead of a folder",
    )
    sync_parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Append to existing playlist instead of replacing tracks",
    )
    sync_parser.add_argument(
        "--basename-fallback",
        action="store_true",
        help="If full path match fails, match by filename only (risky for duplicates)",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would sync without writing",
    )
    sync_parser.add_argument(
        "--no-commit",
        action="store_true",
        help="DB method only: stage changes without calling commit()",
    )
    sync_parser.add_argument(
        "--no-restore-hidden",
        action="store_true",
        help="DB method only: do not clear Rekordbox 'missing' flag on matched files",
    )
    sync_parser.set_defaults(func=cmd_sync)

    sub.add_parser("gui", help="Open the desktop sync UI").set_defaults(func=cmd_gui)
    return parser


def cmd_gui(_args: argparse.Namespace) -> int:
    from .gui import main as gui_main

    gui_main()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "sync" and args.no_parent_folder:
        args.parent_folder = None
    if args.command == "sync" and args.output is None and args.method == "xml":
        args.output = DEFAULT_OUTPUT_XML
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
