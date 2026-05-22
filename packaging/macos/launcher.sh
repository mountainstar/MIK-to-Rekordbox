#!/bin/bash
# macOS app entry point — launches the project venv GUI.
set -euo pipefail

APP_BUNDLE="$(cd "$(dirname "$0")/../.." && pwd)"
RESOURCES="$APP_BUNDLE/Contents/Resources"
PROJECT_ROOT=""

if [[ -f "$RESOURCES/project_root" ]]; then
  PROJECT_ROOT="$(<"$RESOURCES/project_root")"
fi

if [[ -z "$PROJECT_ROOT" || ! -d "$PROJECT_ROOT" ]]; then
  # Fallback: .app sitting inside the repo (e.g. ~/Documents/mik-to-rekordbox/)
  PROJECT_ROOT="$(cd "$APP_BUNDLE/.." && pwd)"
fi

PYTHON="$PROJECT_ROOT/.venv/bin/python"
GUI="$PROJECT_ROOT/mik_sync_gui.py"

if [[ ! -x "$PYTHON" || ! -f "$GUI" ]]; then
  osascript <<EOF 2>/dev/null || true
display alert "MIK to Rekordbox" message "Could not find the project at:
$PROJECT_ROOT

Run scripts/build_mac_app.sh from the mik-to-rekordbox folder after setup." as critical
EOF
  exit 1
fi

cd "$PROJECT_ROOT"
exec "$PYTHON" "$GUI"
