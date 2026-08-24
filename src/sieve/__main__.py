"""`uv run sieve`, or `uv run python -m sieve`."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sieve import responsiveness
from sieve.gui import metrics
from sieve.gui.frame import MainWindow


def main() -> None:
    # Before anything else, and before any thread exists to be starved.
    # The fill and encode threads churn the interpreter hard enough to
    # stop the event loop for a few hundred milliseconds at the default
    # interval; the explorers set this at import and this is that, moved
    # to where an application decides it rather than where a module does.
    responsiveness.apply()
    app = QApplication(sys.argv)
    # The remembered text size, before the first widget exists: it is set on the
    # application's own font, which a widget takes a copy of when it is built, so
    # one installed afterwards would reach only what was made after it. Unlike
    # the palette, which is read at import — a font needs an application to be
    # set on, and there is not one until the line above.
    metrics.install()
    # The title bar is the window's own now — it has to be asked for again every
    # time the palette changes, and half the palettes want the light one, so it
    # is not something an entry point can set once on the way up.
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
