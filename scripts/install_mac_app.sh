#!/bin/bash
# Copy the built .app into /Applications.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="MIK to Rekordbox.app"
SRC="$ROOT/$APP_NAME"
DEST="/Applications/$APP_NAME"

if [[ ! -d "$SRC" ]]; then
  echo "Run ./scripts/build_mac_app.sh first." >&2
  exit 1
fi

echo "Installing to $DEST ..."
rm -rf "$DEST"
ditto "$SRC" "$DEST"

# Re-apply icon on the installed copy (ditto can drop Finder icon metadata)
ICON_SRC="$ROOT/assets/AppIcon.png"
if [[ -f "$ICON_SRC" ]]; then
  osascript <<APPLESCRIPT
use framework "AppKit"
set theImage to current application's NSImage's alloc()'s initWithContentsOfFile:"$ICON_SRC"
current application's NSWorkspace's sharedWorkspace()'s setIcon:theImage forFile:"$DEST" options:0
APPLESCRIPT
fi
xattr -cr "$DEST" 2>/dev/null || true

echo "Done. Launch from Applications or Spotlight."
