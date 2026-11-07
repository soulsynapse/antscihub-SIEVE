"""Where a Qt warning came from: a message handler, on by default, that prints each warning with
the Python stack under it and the widget that had focus, the popup that was open and the widget
under the cursor at that moment, since the stack alone often ends at app.exec() when the call
came from inside Qt. `SIEVE_QT_TRACE=setPointSize` prints only warnings containing that text;
`SIEVE_QT_TRACE=0` leaves Qt's own printing alone. `watchdog` is the matching instrument for a hang."""
import faulthandler
import os
import sys
import traceback

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication


def _name(w):
    return "none" if w is None else f"{type(w).__name__}({w.objectName() or ''}) in {type(w.window()).__name__}"


def install():
    want = os.environ.get("SIEVE_QT_TRACE", "1")
    if want == "0":
        return False
    needle = "" if want == "1" else want

    def handler(mode, ctx, msg):
        if needle not in msg:
            return
        kind = {QtMsgType.QtWarningMsg: "warning", QtMsgType.QtCriticalMsg: "critical"}.get(mode, str(mode))
        app = QApplication.instance()
        print(f"\n[qt {kind}] {msg}", file=sys.stderr)
        if app is not None:
            print(f"  focus: {_name(app.focusWidget())}\n  popup: {_name(app.activePopupWidget())}\n"
                  f"  under cursor: {_name(app.widgetAt(QCursor.pos()))}", file=sys.stderr)
        print("  python stack:", file=sys.stderr)
        traceback.print_stack(file=sys.stderr)
        sys.stderr.flush()

    qInstallMessageHandler(handler)
    return True


def watchdog(app, seconds=5.0, file=None):
    """Dumps every thread's Python stack to `file`, stderr by default, when the GUI thread has not
    turned its event loop for `seconds`, and again every `seconds` while it stays stuck: a timer on
    the GUI thread keeps pushing a faulthandler deadline ahead, and a hang lets it fall due. The
    timer is returned so it lives as long as the caller holds it."""
    from PySide6.QtCore import QTimer

    def arm():
        faulthandler.dump_traceback_later(seconds, repeat=True, file=file or sys.stderr)

    timer = QTimer(app)
    timer.timeout.connect(arm)
    timer.start(int(seconds * 100))
    arm()
    return timer
