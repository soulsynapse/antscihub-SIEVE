"""The `sieve-gui` console entry point, declared in `pyproject.toml`.

Landed together per NOTES.md's stated rule: a script naming a module that does
not exist is the stale-metadata failure this project's packaging replaced, so
the entry point arrives in the same commit as the module it names.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from sieve.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(960, 600)
    window.show()
    if len(sys.argv) > 1:
        window.open_video(sys.argv[1])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
