"""Launch the MIK → Rekordbox desktop UI."""

from __future__ import annotations

import sys


def main() -> None:
    try:
        import tkinter  # noqa: F401
    except ImportError as exc:
        if sys.platform == "darwin":
            hint = (
                "On Homebrew Python, install it with:\n"
                "  brew install python-tk@3.14\n"
                "Then recreate the venv or run the GUI with a Python that includes tkinter."
            )
        elif sys.platform == "win32":
            hint = (
                "Re-run the Python installer and enable 'tcl/tk and IDLE',\n"
                "or use the official python.org installer build."
            )
        else:
            hint = "Install a Python build that includes the tkinter module."
        print(
            f"Tkinter is not available for this Python build.\n{hint}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    from .macos_ui import set_macos_app_name

    set_macos_app_name()

    from .gui_app import run

    run()


if __name__ == "__main__":
    main()
