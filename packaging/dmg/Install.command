#!/bin/bash
# Double-click installer for the MIK to Rekordbox DMG.
set -euo pipefail

APP_NAME="MIK to Rekordbox.app"
VOLUME_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$VOLUME_DIR/$APP_NAME"
DEST="/Applications/$APP_NAME"

if [[ ! -d "$SOURCE" ]]; then
  osascript -e 'display alert "Install failed" message "MIK to Rekordbox.app was not found on this disk." as critical'
  exit 1
fi

echo "Installing MIK to Rekordbox to Applications ..."
ditto "$SOURCE" "$DEST"
xattr -cr "$DEST" 2>/dev/null || true

osascript <<EOF
display notification "Installed to Applications" with title "MIK to Rekordbox"
EOF

open -a "MIK to Rekordbox" 2>/dev/null || open -a Finder "/Applications"

exit 0
