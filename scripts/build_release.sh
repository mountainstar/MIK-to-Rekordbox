#!/bin/bash
# Build a standalone .app and distributable .dmg for other Macs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_NAME="MIK to Rekordbox.app"
DIST_APP="$ROOT/dist/$APP_NAME"
DMG_NAME="MIK-to-Rekordbox.dmg"
DMG_PATH="$ROOT/dist/$DMG_NAME"
ICON_SRC="$ROOT/assets/AppIcon.png"
VENV_PYTHON="$ROOT/.venv/bin/python"
STAGING="$ROOT/build/dmg-staging"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Create the venv first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "$ICON_SRC" ]]; then
  echo "Missing $ICON_SRC" >&2
  exit 1
fi

echo "==> Installing PyInstaller (if needed) ..."
"$VENV_PYTHON" -m pip install -q pyinstaller

echo "==> Building standalone app ..."
rm -rf "$ROOT/build/MIK to Rekordbox" "$ROOT/dist"
"$VENV_PYTHON" -m PyInstaller --noconfirm "$ROOT/mik_sync.spec"

if [[ ! -d "$DIST_APP" ]]; then
  echo "PyInstaller did not produce $DIST_APP" >&2
  exit 1
fi

echo "==> Applying app icon ..."
osascript <<APPLESCRIPT
use framework "AppKit"
set theImage to current application's NSImage's alloc()'s initWithContentsOfFile:"$ICON_SRC"
current application's NSWorkspace's sharedWorkspace()'s setIcon:theImage forFile:"$DIST_APP" options:0
APPLESCRIPT
xattr -cr "$DIST_APP" 2>/dev/null || true

echo "==> Creating DMG ..."
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$DIST_APP" "$STAGING/"
ln -sf /Applications "$STAGING/Applications"
cp "$ROOT/packaging/dmg/README.txt" "$STAGING/README.txt"
cp "$ROOT/packaging/dmg/Install.command" "$STAGING/Install.command"
cp "$ROOT/packaging/dmg/Add CLI command.command" "$STAGING/Add CLI command.command"
chmod +x "$STAGING/Install.command" "$STAGING/Add CLI command.command"

rm -f "$DMG_PATH"
hdiutil create \
  -volname "MIK to Rekordbox" \
  -srcfolder "$STAGING" \
  -ov \
  -format UDZO \
  "$DMG_PATH" >/dev/null

echo ""
echo "Release build complete:"
echo "  App: $DIST_APP ($(du -sh "$DIST_APP" | awk '{print $1}'))"
echo "  DMG: $DMG_PATH ($(du -sh "$DMG_PATH" | awk '{print $1}'))"
echo ""
echo "Upload $DMG_NAME for others to download. They drag the app to Applications."
echo "Built for: $(uname -m) — distribute matching Macs (arm64 Apple Silicon or x86_64 Intel)."
