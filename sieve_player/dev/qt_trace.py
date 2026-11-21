"""Where a Qt warning came from: a message handler, on by default, that prints each warning with
the Python stack under it and the widget that had focus, the popup that was open and the widget
under the cursor at that moment, since the stack alone often ends at app.exec() when the call
came from inside Qt. `SIEVE_QT_TRACE=setPointSize` prints only warnings containing that text;
`SIEVE_QT_TRACE=0` leaves Qt's own printing alone. `watchdog` is the matching instrument for a hang."""
import os
import sys
import threading
import time
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


class _Watch:
    """When the GUI thread last turned its event loop, and whether it is `seconds` since, on
    `clock`. `beat` is the GUI thread's; `overdue` any thread's."""

    def __init__(self, seconds, clock=time.monotonic):
        self.seconds, self.clock = seconds, clock
        self.beaten = self.told = clock()

    def beat(self):
        self.beaten = self.told = self.clock()

    def overdue(self):
        """How long the GUI thread has gone without a beat where that is `seconds` or longer and
        `seconds` since this last said so; else None."""
        now = self.clock()
        if now - self.told < self.seconds:
            return None
        self.told = now
        return now - self.beaten


def dump_stacks(file, stuck):
    """Every thread's Python stack to `file`, under a line saying the GUI thread has been stuck
    `stuck` seconds. A file that will not take the write is passed over."""
    names = {t.ident: t.name for t in threading.enumerate()}
    lines = [f"Timeout: the GUI thread has not turned its event loop for {stuck:.1f} s\n"]
    for ident, frame in sys._current_frames().items():
        lines += [f"Thread {names.get(ident, '?')} (0x{ident:08x}), most recent call last:\n", *traceback.format_stack(frame)]
    try:
        file.write("".join(lines) + "\n")
        file.flush()
    except (OSError, ValueError):
        pass


def watchdog(app, seconds=5.0, file=None):
    """Dumps every thread's Python stack to `file`, stderr by default, when the GUI thread has not
    turned its event loop for `seconds`, and again every `seconds` while it stays stuck: a timer on
    the GUI thread beats, and a thread of its own dumps where the beat is overdue. The timer is
    returned so it lives as long as the caller holds it. A thread that holds the interpreter lock
    and never gives it up is not dumped, the watching thread being unable to run."""
    from PySide6.QtCore import QTimer

    watch = _Watch(seconds)

    def run():
        while True:
            time.sleep(seconds / 10)
            stuck = watch.overdue()
            if stuck is not None:
                # under the interpreter lock: faulthandler's timed dump reads running threads' frames without it and can fault
                dump_stacks(file or sys.stderr, stuck)

    timer = QTimer(app)
    timer.timeout.connect(watch.beat)
    timer.start(int(seconds * 100))
    threading.Thread(target=run, name="watchdog", daemon=True).start()
    return timer
