from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from sieve import __version__
from sieve.decode.quiet import silence_raw_format_warning
from sieve.gui.main_window import MainWindow
from sieve.gui.wheel_steps import WheelSteps


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    silence_raw_format_warning()
    app = QApplication(argv)
    app.setApplicationName("SIEVE")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("AntSciHub")
    app.installEventFilter(WheelSteps(app))
    window = MainWindow()
    window.show()
    if len(argv) > 1:
        window.open_video(Path(argv[1]))
    else:
        window.restore_last_video()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
