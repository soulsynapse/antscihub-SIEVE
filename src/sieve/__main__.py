"""`uv run sieve`, or `uv run python -m sieve`."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sieve.gui.frame import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    # The title bar is the window's own now — it has to be asked for again every
    # time the palette changes, and half the palettes want the light one, so it
    # is not something an entry point can set once on the way up.
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
