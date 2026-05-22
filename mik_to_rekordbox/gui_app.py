"""Tkinter application (import only when tkinter is available)."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk

from .mik_reader import DEFAULT_MIK_DB, MikReader
from .reporting import format_sync_report
from .sync_db import MIK_SYNC_FOLDER, sync_playlist_to_db
from .sync_xml import DEFAULT_XML, sync_playlist_to_xml

DEFAULT_OUTPUT_XML = Path.home() / "Documents/rekordbox/rekordbox_mik_sync.xml"


@dataclass(frozen=True)
class PlaylistRow:
    name: str
    track_count: int

    @property
    def label(self) -> str:
        return f"{self.name} ({self.track_count} tracks)"


def _rekordbox_is_running() -> bool:
    try:
        from pyrekordbox.utils import get_rekordbox_pid

        return bool(get_rekordbox_pid())
    except Exception:
        return False


class MikSyncApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MIK → Rekordbox")
        self.minsize(720, 520)
        self._rows: list[PlaylistRow] = []
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._busy = False

        self._build_ui()
        self._poll_log()
        self.refresh_playlists()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        ttk.Label(root, text="Mixed In Key playlists", font=("", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(root, text="Sync options", font=("", 13, "bold")).grid(
            row=0, column=1, sticky="w", padx=(12, 0)
        )

        list_frame = ttk.Frame(root)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self._listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            activestyle="dotbox",
            exportselection=False,
        )
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scroll.set)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        list_btns = ttk.Frame(list_frame)
        list_btns.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self._btn_refresh = ttk.Button(
            list_btns, text="Refresh", command=self.refresh_playlists
        )
        self._btn_refresh.pack(side=tk.LEFT)
        self._btn_sync = ttk.Button(
            list_btns, text="Sync selected", command=self.sync_selected
        )
        self._btn_sync.pack(side=tk.LEFT, padx=(8, 0))
        self._btn_sync_all = ttk.Button(list_btns, text="Sync all", command=self.sync_all)
        self._btn_sync_all.pack(side=tk.LEFT, padx=(8, 0))

        opts = ttk.Frame(root, padding=(12, 0, 0, 0))
        opts.grid(row=1, column=1, sticky="nsew")
        opts.columnconfigure(0, weight=1)

        self._method = tk.StringVar(value="db")
        ttk.Label(opts, text="Method").grid(row=0, column=0, sticky="w")
        method_row = ttk.Frame(opts)
        method_row.grid(row=1, column=0, sticky="w", pady=(2, 10))
        ttk.Radiobutton(
            method_row, text="Database (recommended)", variable=self._method, value="db"
        ).pack(anchor="w")
        ttk.Radiobutton(
            method_row, text="XML export", variable=self._method, value="xml"
        ).pack(anchor="w")

        self._basename = tk.BooleanVar(value=True)
        self._restore = tk.BooleanVar(value=True)
        self._keep = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts,
            text="Match by filename if path differs",
            variable=self._basename,
        ).grid(row=2, column=0, sticky="w")
        ttk.Checkbutton(
            opts,
            text="Restore tracks Rekordbox marked missing",
            variable=self._restore,
        ).grid(row=3, column=0, sticky="w", pady=(4, 0))
        ttk.Checkbutton(
            opts,
            text="Append instead of replacing playlist",
            variable=self._keep,
        ).grid(row=4, column=0, sticky="w", pady=(4, 0))

        ttk.Label(opts, text="Rekordbox folder").grid(row=5, column=0, sticky="w", pady=(12, 0))
        self._parent_folder = tk.StringVar(value=MIK_SYNC_FOLDER)
        ttk.Entry(opts, textvariable=self._parent_folder).grid(
            row=6, column=0, sticky="ew", pady=(2, 0)
        )

        hint = (
            "Database sync: quit Rekordbox (Cmd+Q) before syncing.\n"
            "XML sync: export collection XML from Rekordbox first."
        )
        ttk.Label(opts, text=hint, wraplength=280, foreground="#555").grid(
            row=7, column=0, sticky="w", pady=(12, 0)
        )

        log_frame = ttk.LabelFrame(root, text="Log", padding=6)
        log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        self._log = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self._log.yview)
        self._log.configure(yscrollcommand=log_scroll.set)
        self._log.grid(row=0, column=0, sticky="nsew")
        log_scroll.grid(row=0, column=1, sticky="ns")

    def _append_log(self, text: str) -> None:
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, text)
        if not text.endswith("\n"):
            self._log.insert(tk.END, "\n")
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _poll_log(self) -> None:
        while True:
            try:
                msg = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(msg)
        self.after(100, self._poll_log)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for widget in (self._btn_refresh, self._btn_sync, self._btn_sync_all):
            widget.configure(state=state)

    def refresh_playlists(self) -> None:
        if self._busy:
            return
        self._listbox.delete(0, tk.END)
        self._rows.clear()
        try:
            reader = MikReader(DEFAULT_MIK_DB)
            for pl in reader.list_playlists():
                if pl.is_folder:
                    continue
                try:
                    count = len(reader.get_playlist_tracks(pl).paths)
                except ValueError:
                    count = 0
                row = PlaylistRow(pl.name, count)
                self._rows.append(row)
                self._listbox.insert(tk.END, row.label)
            self._append_log(f"Loaded {len(self._rows)} MIK playlists.")
        except Exception as exc:
            messagebox.showerror("Refresh failed", str(exc))
            self._append_log(f"Refresh failed: {exc}")

    def _selected_names(self) -> list[str]:
        indices = self._listbox.curselection()
        return [self._rows[i].name for i in indices]

    def sync_selected(self) -> None:
        names = self._selected_names()
        if not names:
            messagebox.showinfo("Select playlists", "Choose one or more playlists to sync.")
            return
        self._start_sync(names)

    def sync_all(self) -> None:
        if not self._rows:
            messagebox.showinfo("No playlists", "Refresh the playlist list first.")
            return
        if not messagebox.askyesno(
            "Sync all",
            f"Sync all {len(self._rows)} playlists into Rekordbox?",
        ):
            return
        self._start_sync([row.name for row in self._rows])

    def _start_sync(self, names: list[str]) -> None:
        if self._busy:
            return
        if self._method.get() == "db" and _rekordbox_is_running():
            if not messagebox.askyesno(
                "Rekordbox is running",
                "Database sync requires Rekordbox to be fully quit (Cmd+Q).\n\n"
                "Continue anyway? (commit will fail if Rekordbox is still open.)",
            ):
                return

        parent = self._parent_folder.get().strip() or None
        self._set_busy(True)
        self._append_log(f"--- Syncing {len(names)} playlist(s) ---")
        threading.Thread(
            target=self._sync_worker,
            args=(names, parent),
            daemon=True,
        ).start()

    def _sync_worker(self, names: list[str], parent_folder: str | None) -> None:
        method = self._method.get()
        method_label = "rekordbox database" if method == "db" else "rekordbox XML"
        exit_code = 0
        try:
            reader = MikReader(DEFAULT_MIK_DB)
            for name in names:
                self._log_queue.put(f"Syncing {name!r}...")
                tracks = reader.get_playlist_tracks(name)
                if method == "xml":
                    report = sync_playlist_to_xml(
                        tracks,
                        xml_path=DEFAULT_XML,
                        parent_folder=parent_folder,
                        replace_existing=not self._keep.get(),
                        allow_basename_fallback=self._basename.get(),
                        output_path=DEFAULT_OUTPUT_XML,
                    )
                else:
                    report = sync_playlist_to_db(
                        tracks,
                        parent_folder=parent_folder,
                        replace_existing=not self._keep.get(),
                        allow_basename_fallback=self._basename.get(),
                        restore_hidden=self._restore.get(),
                    )
                lines, code = format_sync_report(report, method=method_label)
                for line in lines:
                    self._log_queue.put(line)
                exit_code = max(exit_code, code)
                self._log_queue.put("")
        except Exception as exc:
            self._log_queue.put(f"ERROR: {exc}")
            exit_code = 1

        if exit_code == 0:
            self._log_queue.put("Done.")
        else:
            self._log_queue.put("Done with warnings — see log above.")
        self.after(0, self._finish_sync)

    def _finish_sync(self) -> None:
        self._set_busy(False)


def run() -> None:
    app = MikSyncApp()
    app.mainloop()
