"""QApplication bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sieve import __version__
from sieve.gui.main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Run the SIEVE desktop application.

    An optional video path may be passed to skip the open dialog, which is
    what makes a launch-open-first-frame timing straightforward to measure.
    """
    argv = list(sys.argv if argv is None else argv)

    app = QApplication(argv)
    app.setApplicationName("SIEVE")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("AntSciHub")

    window = MainWindow()
    window.show()

    if len(argv) > 1:
        window.open_video(Path(argv[1]))

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
