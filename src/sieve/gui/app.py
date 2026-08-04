"""The one place that mutates process-wide state before any window exists,
and resolves which video a launch opens.

fd 2 is silenced here, before any decoding, rather than in the reader:
taking it is a process-wide act and `main` is what owns the process (see
`decode/quiet.py` for why the log level and the environment variable are
not viable alternatives). The wheel-step event filter is installed on the
`QApplication` for the same reason — every slider and spinbox gets one
detent per step without each widget configuring it itself (see
`wheel_steps.py` for the acceleration rules).

An explicit video path argument wins over the remembered one: the argument
is what the caller asked for now, the preference is what they did last
time. Passing one also skips the open dialog, which is what makes a
launch-to-first-frame timing measurement straightforward.
"""

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
