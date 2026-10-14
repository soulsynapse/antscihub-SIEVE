"""Offscreen smoke test of the player: open empty, load, export, reload, close. No display needed.

    .venv\\Scripts\\python smoke.py [video]

Runs the example chain (rescale -> threshold -> motion) and tools/downsample.
Asserts on state at each step and exits non-zero on the first failure. Text renders as boxes
under the offscreen platform, so there is nothing to look at; this checks wiring, not looks.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player.window import PlayerWindow  # noqa: E402
from tools import downsample as ds, motion, rescale, threshold  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else "video-tests/rep3_intermittent_crop.MP4"
app = QApplication.instance() or QApplication(sys.argv)
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL", msg)


def run_chain():
    win = PlayerWindow([rescale, threshold, motion], "smoke")
    win.resize(1200, 700)
    win.show()
    check(not win.timeline.isEnabled(), "transport enabled before load")
    check(win.outputs.button.isHidden(), "export button shown for a chain with no exporter")
    win.toggle_play(), win.goto(5, True), win.set_window(0, 10)  # must all be no-ops
    win.load("definitely/not/a/file.mp4")
    check(win.chain is None and "could not open" in win.inputs.info.text(), "bad path not reported")
    win.load(path)
    check(win.chain is not None and win.timeline.isEnabled(), "load did not enable the player")
    check(win.windowTitle().endswith(os.path.basename(path)), "title not updated on load")

    def after():
        check(win.result is not None and "gate" in win.result, "series result never arrived")
        win.load(path)  # reload replaces decoder and worker
        check(win.chain is not None, "reload failed")
        win.close()
        app.quit()

    QTimer.singleShot(2500, after)
    app.exec()


def run_downsample():
    win = PlayerWindow([ds], "smoke")
    win.resize(1200, 700)
    win.show()
    check(not win.outputs.button.isEnabled(), "export enabled before load")
    win.load(path)
    dst = win.outputs._target()
    check(not os.path.exists(dst), f"target already exists: {dst}")
    win.outputs.button.click()
    check(win.outputs.button.text() == "Cancel", "export did not start")

    def after():
        check(os.path.exists(dst), "export wrote nothing")
        check(win.outputs.status.text().startswith("wrote"), f"status: {win.outputs.status.text()}")
        if os.path.exists(dst):
            os.remove(dst)
        win.close()
        app.quit()

    QTimer.singleShot(20000, after)
    app.exec()


run_chain()
run_downsample()
print("smoke:", "ok" if not failures else f"{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
