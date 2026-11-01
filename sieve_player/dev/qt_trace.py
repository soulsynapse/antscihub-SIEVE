"""Where a Qt warning came from. `SIEVE_QT_TRACE=1` installs a message handler that prints each
warning with the Python stack under it and the widget that had focus, the popup that was open and
the widget under the cursor at that moment, since the stack alone often ends at app.exec() when
the call came from inside Qt. `SIEVE_QT_TRACE=setPointSize` prints only warnings containing that
text."""
import os
import sys
import traceback

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication


def _name(w):
    return "none" if w is None else f"{type(w).__name__}({w.objectName() or ''}) in {type(w.window()).__name__}"


def install():
    want = os.environ.get("SIEVE_QT_TRACE", "")
    if not want:
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
