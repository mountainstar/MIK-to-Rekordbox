# PyInstaller spec for distributable macOS app.
# Build: .venv/bin/pyinstaller mik_sync.spec

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
root = Path(SPECPATH)

hidden = [
    "pyrekordbox",
    "pyrekordbox.db6",
    "pyrekordbox.db6.tables",
    "pyrekordbox.db6.aux_files",
    "pyrekordbox.db6.registry",
    "pyrekordbox.config",
    "sqlcipher3",
    "Foundation",
    "AppKit",
]

a = Analysis(
    [str(root / "mik_sync_gui.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[],
    hiddenimports=hidden + collect_submodules("pyrekordbox"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MIK to Rekordbox",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MIK to Rekordbox",
)

app = BUNDLE(
    coll,
    name="MIK to Rekordbox.app",
    icon=None,
    bundle_identifier="com.mik-to-rekordbox.app",
    info_plist={
        "CFBundleName": "MIK to Rekordbox",
        "CFBundleDisplayName": "MIK to Rekordbox",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
    },
)
