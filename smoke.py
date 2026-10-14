"""Offscreen smoke test of the player: open empty, load, export, reload, close. No display needed.

    .venv\\Scripts\\python smoke.py [video]

Runs the example chain (gray -> rescale -> threshold -> motion) and tools/downsample.
Asserts on state at each step and exits non-zero on the first failure. Text renders as boxes
under the offscreen platform, so there is nothing to look at; this checks wiring, not looks.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player.window import PlayerWindow  # noqa: E402
from tools import downsample as ds, gray, motion, rescale, threshold  # noqa: E402

path = sys.argv[1] if len(sys.argv) > 1 else "video-tests/rep3_intermittent_crop.MP4"
app = QApplication.instance() or QApplication(sys.argv)
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL", msg)


def run_chain():
    win = PlayerWindow([gray, rescale, threshold, motion], "smoke")
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
        check(win.links.sources == [-1, 0, 1] and win.links.series_source == 2, f"default wiring {win.links.sources}")
        check(len(win.column.strips) == 5 and win.column.strips[2].text == "gray from rescale", "strip text")
        check(not win.column.rail.dead, "a fully read chain reports an unread stage")
        # open threshold alone: the frame shows its stage, Input offers the video's gray stages
        win.focus(2)
        check(win.focused == 2 and win.links.shown == 2, "focus did not open")
        check(win.cards[2].buttons.isVisible() and win.source_card.isVisible(), "focus column not shown")
        check([win.source_pick.itemData(i) for i in range(win.source_pick.count())] == [0, 1], "source picker")
        thresh = win.frame_widgets[2]
        before = dict(thresh.params())
        thresh.set_params({"thresh": 200})
        win.source_pick.setCurrentIndex(0)   # read gray directly, skipping rescale
        check(win.links.sources[2] == 0, "rewire did not land")
        check(win.chain.links is win.links, "chain holds a different wiring")
        boxes = [c for _, c in win.sink_card.form.rows]
        check(len(boxes) == 1 and boxes[0].isChecked(), "Output should list motion, reading threshold")
        boxes[0].setChecked(False)   # motion reads rescale instead; threshold is now unread
        check(win.links.series_source == 1 and win.cards[2] in win.column.rail.dead, "detach did not land")
        win.cancel()
        check(win.focused is None and win.links.sources[2] == 1 and win.links.series_source == 2
              and thresh.params() == before, "cancel did not restore")
        win.focus(2)
        win.source_pick.setCurrentIndex(0)
        win.save()
        check(win.links.sources[2] == 0 and win.links.shown == 2, "save did not keep")
        check(win.cards[1] in win.column.rail.dead and win.column.strips[2].unused == "gray unread",
              "rescale not flagged unread")
        # pointing rescale at the video makes it hand out bgr; threshold reads gray, so it is re-pointed
        win.links.set_source(2, 1)
        win.links.set_source(1, -1)
        check(win.links.produces(1) == "bgr" and win.links.sources[2] == 0, f"re-default {win.links.sources}")
        win.load(path)  # reload replaces decoder and worker, keeps the wiring
        check(win.chain is not None and win.chain.links.sources == [-1, -1, 0], "reload lost the wiring")
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
