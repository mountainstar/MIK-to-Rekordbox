"""macOS menu bar / process name helpers for Tk apps launched via Python."""

from __future__ import annotations

import sys

APP_NAME = "MIK to Rekordbox"


def set_macos_app_name(name: str = APP_NAME) -> None:
    """Show *name* in the macOS menu bar instead of 'Python'."""
    if sys.platform != "darwin":
        return

    if _set_via_appkit(name):
        return
    _set_via_py_setprogramname(name)


def _set_via_appkit(name: str) -> bool:
    try:
        from Foundation import NSBundle, NSProcessInfo
    except ImportError:
        return False

    NSProcessInfo.processInfo().setProcessName_(name)
    info = NSBundle.mainBundle().infoDictionary()
    if info is not None:
        info["CFBundleName"] = name
        info["CFBundleDisplayName"] = name
    return True


def _set_via_py_setprogramname(name: str) -> None:
    try:
        import ctypes

        ctypes.pythonapi.Py_SetProgramName(ctypes.c_wchar_p(name))
    except Exception:
        pass
