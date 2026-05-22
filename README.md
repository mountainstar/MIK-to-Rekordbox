# mik-to-rekordbox

Sync **Mixed In Key 11** playlists into **Rekordbox** automatically, preserving track order from your MIK crate.

Mixed In Key stores playlists in `Collection11.mikdb` (SQLite). This tool reads that database and creates matching playlists in Rekordbox by matching file paths.

## Requirements

- macOS (tested with MIK 11 + Rekordbox 7)
- Python 3.11+
- Tracks must already exist in your Rekordbox library (same files MIK analyzed)

## Setup

```bash
cd ~/Documents/mik-to-rekordbox
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Launch from Dock (macOS app)

After [setup](#setup), build the app once:

```bash
./scripts/build_mac_app.sh
```

This creates **`MIK to Rekordbox.app`** in the project folder. Double-click it in Finder, or install to Applications:

```bash
./scripts/install_mac_app.sh
```

Then open from Applications or Spotlight, and optionally **Keep in Dock** (right-click the icon → Options).

The app remembers where the project lives. If you move the `mik-to-rekordbox` folder, run `build_mac_app.sh` again.

### Distributable DMG (for other Macs)

Build a **standalone** app (no Python install required) and a download-ready `.dmg`:

```bash
./scripts/build_release.sh
```

Output: `dist/MIK-to-Rekordbox.dmg` — upload/share that file. Recipients drag the app to Applications.

The DMG is built for your Mac’s CPU (Apple Silicon or Intel). Build on the architecture you want to support, or build both and ship two DMGs.

### GUI (terminal)

```bash
.venv/bin/python mik_sync_gui.py
```

Or: `.venv/bin/python mik_sync.py gui`

Select MIK playlists, choose **Database (recommended)**, quit Rekordbox (Cmd+Q), then click **Sync selected**.

If the GUI fails to start with a `tkinter` / `_tkinter` error (common with Homebrew Python):

```bash
brew install python-tk@3.14
```

If you just created or renamed a playlist in Mixed In Key and it does not appear in the list yet, switch to another playlist in MIK (or wait a few seconds) so MIK saves to `Collection11.mikdb`, then click **Refresh**.

### List MIK playlists

```bash
.venv/bin/python mik_sync.py list
```

### Sync a playlist (recommended: XML method)

1. In **Rekordbox**: **File → Export Collection in XML format** → save as `~/Documents/rekordbox/rekordbox.xml`
2. Run sync (writes a separate XML so your export stays intact):

```bash
.venv/bin/python mik_sync.py sync "05/19/2026"
```

3. In **Rekordbox**:
   - **File → Export Collection in XML format** first (refreshes track list for matching)
   - **Preferences → Advanced** → set XML import path to `~/Documents/rekordbox/rekordbox_mik_sync.xml`
   - Click the **XML refresh** button in the left tree
   - Open **MIK Sync → your playlist**
   - Right-click → **Import Playlist**

The sync file is rebuilt from your latest export each time: deleted MIK playlists are removed from **MIK Sync**, and only current MIK playlists appear. Use **XML** as the sync method in the GUI (not Database) for this workflow.

### Sync directly to `master.db` (advanced)

Close Rekordbox completely (**Cmd+Q** — the app must not be running), then:

```bash
.venv/bin/python mik_sync.py sync "05/19/2026" --method db --basename-fallback
```

If a playlist shows fewer tracks than `Matched:` in the terminal, Rekordbox may have those files marked missing (`rb_local_deleted`) even though they still exist on disk. The DB sync clears that flag automatically for matched files with `--basename-fallback` (default). Use `--no-restore-hidden` to skip.

Reopen Rekordbox. Playlists appear under **MIK Sync** in your tree.

### Options

| Flag | Description |
|------|-------------|
| `--all` | Sync every MIK playlist |
| `--method xml\|db` | XML export (default) or direct database write |
| `--basename-fallback` | Match by filename if full path fails |
| `--dry-run` | Preview track counts only |
| `--no-parent-folder` | Put playlists at root instead of `MIK Sync` |

## How matching works

1. Read ordered file paths from MIK (`Z_1SONGS` + macOS bookmark blobs)
2. Normalize paths and look them up in Rekordbox (XML `Location` or DB `FolderPath`)
3. Build the playlist with Rekordbox `TrackID`s in the same order

Unmatched files are listed at the end — usually means the track is not in your Rekordbox collection yet.

## Paths (defaults)

| Item | Location |
|------|----------|
| MIK database | `~/Library/Application Support/Mixedinkey/Collection11.mikdb` |
| Rekordbox XML | `~/Documents/rekordbox/rekordbox.xml` |
| Sync output XML | `~/Documents/rekordbox/rekordbox_mik_sync.xml` |

## Note on MIK cue points

If you use **Mixed In Key → Export Cue Points → Rekordbox**, MIK already maintains `rekordbox.xml` with cue data. This tool is for **playlist order** from MIK crates, not cue-point export. You can use both workflows with different XML files.
