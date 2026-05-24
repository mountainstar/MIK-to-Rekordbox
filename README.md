# mik-to-rekordbox

Sync **Mixed In Key 11** playlists into **Rekordbox** automatically, preserving track order from your MIK crate.

Mixed In Key stores playlists in `Collection11.mikdb` (SQLite). This tool reads that database and creates matching playlists in Rekordbox by matching file paths.

## Requirements

- **macOS** 12+ or **Windows** 10+ (tested with MIK 11 + Rekordbox 7)
- Python 3.11+ (for development; end users can use the release downloads)
- Tracks must already exist in your Rekordbox library (same files MIK analyzed)

## Setup

**macOS / Linux:**

```bash
cd ~/Documents/mik-to-rekordbox
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
cd $env:USERPROFILE\Documents\mik-to-rekordbox
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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

### Download (recommended)

**[GitHub Releases](https://github.com/mountainstar/MIK-to-Rekordbox/releases)**

| Platform | File |
|----------|------|
| Apple Silicon Mac | `MIK-to-Rekordbox-arm64.dmg` |
| Intel Mac | `MIK-to-Rekordbox-x86_64.dmg` |
| Windows 64-bit | `MIK-to-Rekordbox-win64.zip` (extract, run `MIK-to-Rekordbox.exe`) |

**macOS:** open the DMG → double-click **Install.command** (or drag the app to **Applications**).

**Windows:** extract the zip → run **MIK-to-Rekordbox.exe** (allow through SmartScreen on first launch if prompted).

### Publish a new release

Pushing a version tag builds macOS DMGs + Windows zip and uploads them automatically:

```bash
git tag v1.0.0
git push origin v1.0.0
```

That triggers the [Release workflow](.github/workflows/release.yml). Manual runs from the Actions tab build artifacts only; tag push creates the GitHub Release.

**Build locally** (optional):

```bash
./scripts/build_release.sh          # macOS → dist/MIK-to-Rekordbox.dmg
```

```powershell
.\scripts\build_release_win.ps1     # Windows → dist\MIK-to-Rekordbox-win64.zip
```

**macOS optional:** **Add CLI command.command** in the DMG creates `/usr/local/bin/mik-sync`.

### GUI (terminal)

```bash
.venv/bin/python mik_sync_gui.py
```

Or: `.venv/bin/python mik_sync.py gui`

Select MIK playlists, choose **Database (recommended)**, fully quit Rekordbox, then click **Sync selected**.

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

Close Rekordbox completely (the app must not be running), then:

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

1. Read ordered file paths from MIK (`Z_1SONGS` + bookmark blobs)
2. Normalize paths and look them up in Rekordbox (XML `Location` or DB `FolderPath`)
3. Build the playlist with Rekordbox `TrackID`s in the same order

Unmatched files are listed at the end — usually means the track is not in your Rekordbox collection yet.

## Paths (defaults)

| Item | macOS | Windows |
|------|-------|---------|
| MIK database | `~/Library/Application Support/Mixedinkey/Collection11.mikdb` | `%LOCALAPPDATA%\Mixedinkey\Collection11.mikdb` (also checks `Mixed In Key` folders) |
| Rekordbox XML | `~/Documents/rekordbox/rekordbox.xml` | `%USERPROFILE%\Documents\rekordbox\rekordbox.xml` |
| Sync output XML | `~/Documents/rekordbox/rekordbox_mik_sync.xml` | `%USERPROFILE%\Documents\rekordbox\rekordbox_mik_sync.xml` |

Override with `--mik-db` if your MIK database is in a custom location.

## Note on MIK cue points

If you use **Mixed In Key → Export Cue Points → Rekordbox**, MIK already maintains `rekordbox.xml` with cue data. This tool is for **playlist order** from MIK crates, not cue-point export. You can use both workflows with different XML files.
