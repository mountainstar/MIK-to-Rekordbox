"""Launch the MIK → Rekordbox desktop UI."""

from __future__ import annotations

import sys


def main() -> None:
    try:
        import tkinter  # noqa: F401
    except ImportError as exc:
        print(
            "Tkinter is not available for this Python build.\n"
            "On Homebrew Python, install it with:\n"
            "  brew install python-tk@3.14\n"
            "Then recreate the venv or run the GUI with a Python that includes tkinter.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    from .gui_app import run

    run()


if __name__ == "__main__":
    main()
