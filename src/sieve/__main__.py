"""`uv run sieve`, or `uv run python -m sieve`."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sieve.gui import metrics
from sieve.gui.frame import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    # Must precede any widget: widgets copy the app font at construction.
    metrics.install()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
