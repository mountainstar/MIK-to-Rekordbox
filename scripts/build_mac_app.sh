#!/bin/bash
# Build "MIK to Rekordbox.app" for Dock / Applications launch.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="MIK to Rekordbox.app"
APP_PATH="$ROOT/$APP_NAME"
ICON_SRC="$ROOT/assets/AppIcon.png"
ICONSET="$ROOT/build/AppIcon.iconset"
ICNS="$ROOT/build/AppIcon.icns"

if [[ ! -f "$ICON_SRC" ]]; then
  echo "Missing $ICON_SRC" >&2
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Run setup first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

echo "Building $APP_NAME ..."
rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS" "$APP_PATH/Contents/Resources" "$ROOT/build"

cp "$ROOT/packaging/macos/Info.plist" "$APP_PATH/Contents/Info.plist"
cp "$ROOT/packaging/macos/launcher.sh" "$APP_PATH/Contents/MacOS/launcher"
chmod +x "$APP_PATH/Contents/MacOS/launcher"
printf '%s\n' "$ROOT" >"$APP_PATH/Contents/Resources/project_root"

# Build .icns from PNG (macOS iconutil)
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
sips -z 16 16 "$ICON_SRC" --out "$ICONSET/icon_16x16.png" >/dev/null
sips -z 32 32 "$ICON_SRC" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$ICON_SRC" --out "$ICONSET/icon_32x32.png" >/dev/null
sips -z 64 64 "$ICON_SRC" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$ICON_SRC" --out "$ICONSET/icon_128x128.png" >/dev/null
sips -z 256 256 "$ICON_SRC" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$ICON_SRC" --out "$ICONSET/icon_256x256.png" >/dev/null
sips -z 512 512 "$ICON_SRC" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$ICON_SRC" --out "$ICONSET/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$ICON_SRC" --out "$ICONSET/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET" -o "$ICNS"
cp "$ICNS" "$APP_PATH/Contents/Resources/AppIcon.icns"

# Mark as a proper application bundle (not a generic folder with custom bit)
touch "$APP_PATH"
if command -v SetFile >/dev/null 2>&1; then
  SetFile -a B "$APP_PATH" 2>/dev/null || true
  SetFile -d C "$APP_PATH" 2>/dev/null || true
fi

# Apply icon via Finder so it shows correctly in Dock / Applications
osascript <<APPLESCRIPT
use framework "AppKit"
set iconPath to "$ICON_SRC"
set appPath to "$APP_PATH"
set theImage to current application's NSImage's alloc()'s initWithContentsOfFile:iconPath
if theImage is missing value then error "Could not load icon image"
current application's NSWorkspace's sharedWorkspace()'s setIcon:theImage forFile:appPath options:0
APPLESCRIPT

xattr -cr "$APP_PATH" 2>/dev/null || true

echo ""
echo "Created: $APP_PATH"
echo ""
echo "Next steps:"
echo "  • Double-click the app in Finder"
echo "  • Drag \"$APP_NAME\" to Applications (optional)"
echo "  • Right-click → Options → Keep in Dock"
echo ""
echo "If you move the project folder, re-run: ./scripts/build_mac_app.sh"
