"""Offscreen smoke test of the player: open empty, load, rewire, save, reopen, export, close. No
display needed.

    .venv\\Scripts\\python smoke.py [video]

Runs the example chain (gray -> rescale -> threshold -> motion -> reduce) in a graph built from a list,
then the same chain and tools/downsample in the window.
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
from tools import downsample as ds, gray, motion, file, reduce, rescale, threshold  # noqa: E402

path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "video-tests/rep3_intermittent_crop.MP4")
app = QApplication.instance() or QApplication(sys.argv)
failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL", msg)


def run_graph():
    """The chain, wired by from_tools with the selector into the video, computed through the graph
    the way the worker will."""
    tools = [file, gray, rescale, threshold, motion, reduce]
    doc = document.from_tools(tools)
    doc.node("file").params.update(folder=os.path.dirname(path), pattern=os.path.basename(path))
    check([(w.src, w.dst) for w in doc.wires] == [("file", "video"), ("video", "gray"), ("gray", "rescale"),
                                                  ("rescale", "threshold"), ("threshold", "motion"), ("motion", "reduce")],
          f"wiring {[(w.src, w.dst) for w in doc.wires]}")
    check(not document.validate(doc, tools), f"document invalid: {document.validate(doc, tools)}")
    picked, why = document.pick_video(doc, tools)
    check(picked is not None and os.path.samefile(picked, path), f"file answered {picked!r} {why}")
    dec = Decoder(picked)
    g = Graph(doc, dec, tools)
    check(g.shown == "motion" and g.walk == "motion" and g.series == "reduce",
          f"flag/walk/series {g.shown} {g.walk} {g.series}")
    check(g.compute("file", 0) is None, "a selector computed a row")
    out = g.compute("motion", 0)
    check(out is not None and out.ndim == 2 and out.dtype == np.uint8, "motion output")
    check(g.peek(0) is out, "peek did not find the shown row")
    stack = np.stack([g.walk_row(r) for r in range(5)])   # through reduce's fold, as the worker does
    result = g.series_tool.run(Series(stack, g.key(g.walk), 0, g.fps), g.series_params())
    check(len(result["signal"]) == 5 and len(result["gate"]) == 5, "reduce series")
    key = g.key("threshold")
    doc.node("threshold").params["thresh"] = 200
    g.sync()
    check(g.key("threshold") != key and g.compute("motion", 0) is not out, "param change did not reach the graph")
    doc.disconnect("rescale")
    g.sync()
    check(g.compute("motion", 0) is None and g.peek(0) is None, "unwired node still computed")
    dec.close()


def run_window():
    tools = [gray, rescale, threshold, motion, reduce]
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
        check(set(win.results) == {"reduce"} and "gate" in win.results["reduce"], "series results never arrived")
        check([(w.src, w.dst) for w in doc.wires] == [("video", "gray"), ("gray", "rescale"), ("rescale", "threshold"),
                                                      ("threshold", "motion"), ("motion", "reduce")], f"default wiring {doc.wires}")
        check(doc.display == "motion" and win.graph.shown == "motion", "the flag should start on the last fed frame node")
        check(doc.overlay is None and win.graph.over is None and win.display._over is None, "the overlay should start off")
        gen = win.worker._gen
        win.canvas.set_overlay("threshold")
        check(win.graph.over == "threshold", "the overlay flag did not reach the runtime")
        check(win.worker._gen == gen, "a flag restarted the walk")
        check(win.display.reason == "" and win.graph.peek(win.row) is not None, "the flagged node is not on the frame")
        # selection drives the pane; the flag stays
        win.canvas.select(["gray", "rescale"])
        check(win.pane.current == "rescale" and not win.pane.cards["threshold"].isVisible(), "pane does not follow selection")
        check(win.graph.shown == "motion", "selecting moved the flag")
        # a knob writes to the document and reaches the runtime
        key = win.graph.key("threshold")
        win.pane.widget("threshold").set_params({"thresh": 200})
        check(doc.node("threshold").params["thresh"] == 200 and win.graph.key("threshold") != key,
              "param change did not reach the document and the graph")
        # the flag moves the frame
        win.canvas.set_flag("gray")
        check(doc.display == "gray" and win.graph.shown == "gray", "flag did not move")
        # unwiring upstream of the flagged node blanks the frame and says why; the flag stays put
        win.canvas.set_flag("motion")
        doc.disconnect("rescale")
        win.sync()
        check(not win.graph.fed("motion") and win.display.reason == "motion: no input" and doc.display == "motion",
              f"unfed flag {win.display.reason!r}")
        doc.connect("gray", "rescale")
        win.sync()
        win.graph.compute("motion", win.row)   # what the worker would deliver; the frame clears on arrival
        win.goto(win.row, commit=True)
        check(win.graph.fed("motion") and win.display.reason == "", "rewire did not land")
        # save, then open the file in another window: same nodes, places, params, flag and video
        saved = os.path.join(tempfile.mkdtemp(), "smoke.json")
        win.save_document(saved)
        check(doc.path == saved, "save did not record where")
        again = PlayerWindow(saved, "smoke", tools)
        check(again.doc.nodes == doc.nodes and again.doc.wires == doc.wires and again.doc.display == "motion",
              "reopened document differs")
        check(again.graph is not None and again.doc.video == path, "reopened document did not open its video")
        check(again.pane.widget("threshold").params()["thresh"] == 200, "reopened knob not at the saved value")
        again.close()
        # reload replaces decoder and worker and keeps the document
        win.load(path)
        check(win.graph is not None and win.doc is doc and win.graph.shown == "motion", "reload lost the document")
        # deleting a node in the middle of a chain takes its wires, its card, and what it fed
        win.canvas.select(["rescale"])
        win.canvas.delete_selected()
        check([(w.src, w.dst) for w in doc.wires] == [("video", "gray"), ("threshold", "motion"), ("motion", "reduce")],
              f"delete left {doc.wires}")
        check("rescale" not in win.pane.cards and win.pane.current is None, "the deleted node's card stayed")
        check(not win.graph.fed("motion") and win.display.reason == "motion: no input", "delete did not reach the runtime")
        # deleting the flagged node leaves no flag and empty ground
        win.canvas.select(["motion"])
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
