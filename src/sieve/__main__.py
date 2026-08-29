"""`uv run sieve`, or `uv run python -m sieve`."""

from __future__ import annotations

import sys

# Before Qt, and before any thread: at the default 5 ms switch interval the
# fill and encode threads starved the GUI thread for 100-400 ms, measured with
# a heartbeat probe — `docs/findings/2026.08.22-what-froze-the-felt-loop.md`.
# A little throughput for an event loop that stays alive.
sys.setswitchinterval(0.002)

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve.gui import metrics  # noqa: E402
from sieve.gui.frame import MainWindow  # noqa: E402


def main() -> None:
    app = QApplication(sys.argv)
    # Must precede any widget: widgets copy the app font at construction.
    metrics.install()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
