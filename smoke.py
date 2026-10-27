"""Offscreen smoke test of the player: open empty, load, rewire, save, reopen, export, close. No
display needed.

    .venv\\Scripts\\python smoke.py [video]

Runs the dummies in a graph built from a list, then the example chain (gray -> rescale ->
threshold -> motion) and tools/downsample in the window.
Asserts on state at each step and exits non-zero on the first failure. Text renders as boxes
under the offscreen platform, so there is nothing to look at; this checks wiring, not looks.
"""
import os
import sys
import tempfile

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, Series  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from dummies import either, flat, keep_gray, passthru, to_gray, writer  # noqa: E402
from tools import downsample as ds, gray, motion, rescale, threshold  # noqa: E402

path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "video-tests/rep3_intermittent_crop.MP4")
app = QApplication.instance() or QApplication(sys.argv)
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL", msg)


def run_graph():
    """The dummies, wired by from_tools, computed through the graph the way the worker will."""
    dummies = [to_gray, passthru, keep_gray, either, writer, flat]
    doc = document.from_tools(dummies, path)
    check([(w.src, w.dst) for w in doc.wires] == [("video", "to_gray"), ("to_gray", "passthru"), ("passthru", "keep_gray"),
                                                  ("keep_gray", "either"), ("either", "writer"), ("writer", "flat")],
          f"dummy wiring {[(w.src, w.dst) for w in doc.wires]}")
    check(not document.validate(doc, dummies), f"dummy document invalid: {document.validate(doc, dummies)}")
    dec = Decoder(path)
    g = Graph(doc, dec, dummies)
    check(g.shown == "writer" and g.walk == "writer" and g.series == "flat", f"flag/walk/series {g.shown} {g.walk} {g.series}")
    out = g.compute("writer", 0)
    check(out is not None and out.shape == (dec.height, dec.width) and out.dtype == np.uint8, "writer output")
    check(g.peek(0) is out, "peek did not find the shown row")
    stack = np.stack([g.compute(g.walk, r) for r in range(5)])
    result = g.series_tool.run(Series(stack, g.key(g.walk), 0, g.fps), g.series_params())
    check(len(result["value"]) == 5 and result["gate"].all(), "flat series")
    doc.node("to_gray").params["level"] = 7
    g.sync()
    check(g.compute("keep_gray", 0).max() == 7 and g.compute("writer", 0).max() == 0, "param change did not reach the graph")
    doc.disconnect("either")
    g.sync()
    check(g.compute("writer", 0) is None and g.peek(0) is None, "unwired node still computed")
    dec.close()


def run_window():
    tools = [gray, rescale, threshold, motion]
    win = PlayerWindow(tools, "smoke")
    win.resize(1200, 700)
    win.show()
    check(not win.timeline.isEnabled(), "transport enabled before load")
    check(win.pane.video is not None and not win.pane.exports, "the pane should hold the video picker and no export")
    win.toggle_play(), win.goto(5, True), win.set_window(0, 10)  # must all be no-ops
    win.load("definitely/not/a/file.mp4")
    check(win.graph is None and "could not open" in win.pane.video.info.text(), "bad path not reported")
    check(win.doc.video is None, "a path that will not open was recorded")
    win.load(path)
    check(win.graph is not None and win.timeline.isEnabled(), "load did not enable the player")
    check(win.windowTitle().endswith(os.path.basename(path)) and win.doc.video == path, "title or document not updated on load")

    def after():
        doc = win.doc
        check(win.result is not None and "gate" in win.result, "series result never arrived")
        check([(w.src, w.dst) for w in doc.wires] == [("video", "gray"), ("gray", "rescale"), ("rescale", "threshold"),
                                                      ("threshold", "motion")], f"default wiring {doc.wires}")
        check(doc.display == "threshold" and win.graph.shown == "threshold", "the flag should start on the last fed frame node")
        check(win.display.reason == "" and win.graph.peek(win.row) is not None, "the flagged node is not on the frame")
        # selection drives the pane; the flag stays
        win.canvas.select(["gray", "rescale"])
        check(win.pane.current == "rescale" and not win.pane.cards["threshold"].isVisible(), "pane does not follow selection")
        check(win.graph.shown == "threshold", "selecting moved the flag")
        # a knob writes to the document and reaches the runtime
        key = win.graph.key("threshold")
        win.pane.widget("threshold").set_params({"thresh": 200})
        check(doc.node("threshold").params["thresh"] == 200 and win.graph.key("threshold") != key,
              "param change did not reach the document and the graph")
        # the flag moves the frame
        win.canvas.set_flag("gray")
        check(doc.display == "gray" and win.graph.shown == "gray", "flag did not move")
        # unwiring upstream of the flagged node blanks the frame and says why; the flag stays put
        win.canvas.set_flag("threshold")
        doc.disconnect("rescale")
        win.sync()
        check(not win.graph.fed("threshold") and win.display.reason == "threshold: no input" and doc.display == "threshold",
              f"unfed flag {win.display.reason!r}")
        doc.connect("gray", "rescale")
        win.sync()
        win.graph.compute("threshold", win.row)   # what the worker would deliver; the frame clears on arrival
        win.goto(win.row, commit=True)
        check(win.graph.fed("threshold") and win.display.reason == "", "rewire did not land")
        # save, then open the file in another window: same nodes, places, params, flag and video
        saved = os.path.join(tempfile.mkdtemp(), "smoke.json")
        win.save_document(saved)
        check(doc.path == saved, "save did not record where")
        again = PlayerWindow(saved, "smoke", tools)
        check(again.doc.nodes == doc.nodes and again.doc.wires == doc.wires and again.doc.display == "threshold",
              "reopened document differs")
        check(again.graph is not None and again.doc.video == path, "reopened document did not open its video")
        check(again.pane.widget("threshold").params()["thresh"] == 200, "reopened knob not at the saved value")
        again.close()
        # reload replaces decoder and worker and keeps the document
        win.load(path)
        check(win.graph is not None and win.doc is doc and win.graph.shown == "threshold", "reload lost the document")
        # deleting a node in the middle of a chain takes its wires, its card, and what it fed
        win.canvas.select(["rescale"])
        win.canvas.delete_selected()
        check([(w.src, w.dst) for w in doc.wires] == [("video", "gray"), ("threshold", "motion")], f"delete left {doc.wires}")
        check("rescale" not in win.pane.cards and win.pane.current is None, "the deleted node's card stayed")
        check(not win.graph.fed("threshold") and win.display.reason == "threshold: no input", "delete did not reach the runtime")
        # deleting the flagged node leaves no flag and empty ground
        win.canvas.select(["threshold"])
        win.canvas.delete_selected()
        check(doc.display is None and win.graph.shown is None and win.display.reason == "" and win.display._pix is None,
              "deleting the flagged node did not clear the frame")
        win.close()
        app.quit()

    QTimer.singleShot(2500, after)
    app.exec()


def run_downsample():
    win = PlayerWindow([ds], "smoke")
    win.resize(1200, 700)
    win.show()
    ex = win.pane.exports["downsample"]
    check(not ex.button.isEnabled(), "export enabled before load")
    win.load(path)
    dst = ex._target()
    check(not os.path.exists(dst), f"target already exists: {dst}")
    ex.button.click()
    check(ex.button.text() == "Cancel", "export did not start")

    def after():
        check(os.path.exists(dst), "export wrote nothing")
        check(ex.status.text().startswith("wrote"), f"status: {ex.status.text()}")
        if os.path.exists(dst):
            os.remove(dst)
        win.close()
        app.quit()

    QTimer.singleShot(20000, after)
    app.exec()


run_graph()
run_window()
run_downsample()
print("smoke:", "ok" if not failures else f"{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
