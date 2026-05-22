#!/bin/bash
# Optional: add `mik-sync` terminal command (requires app installed in Applications).
set -euo pipefail

APP="/Applications/MIK to Rekordbox.app/Contents/MacOS/MIK to Rekordbox"
LINK="/usr/local/bin/mik-sync"

if [[ ! -x "$APP" ]]; then
  osascript -e 'display alert "Not installed" message "Install MIK to Rekordbox to Applications first (run Install.command or drag the app)." as critical'
  exit 1
fi

mkdir -p "$(dirname "$LINK")"
ln -sf "$APP" "$LINK"

osascript -e 'display alert "CLI command added" message "You can now run: mik-sync\n\n(Requires the app to be installed in Applications.)"'
