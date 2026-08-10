"""`uv run sieve`, or `uv run python -m sieve`."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sieve.gui.frame import MainWindow
from sieve.gui.frame.chrome import darken_title_bar


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    darken_title_bar(window)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
