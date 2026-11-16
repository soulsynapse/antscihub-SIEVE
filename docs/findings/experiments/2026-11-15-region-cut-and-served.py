"""One-off: a region cut by ffmpeg on two seconds of the crossings clip, then served through an offscreen
PlayerWindow: the served key against a standalone document's, a scrub's reads, a second cut over the served
clip, another shape, no choice, a shape moved. Run from the repo root; the work folder is deleted and made again:
python docs/findings/experiments/2026-11-15-region-cut-and-served.py <work folder> <clip> <geometry.json>"""
import os
import shutil
import subprocess
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder, footage_print  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.plan import base_key  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tools import csv, gray, reduce, region  # noqa: E402

work, clip, geometry = sys.argv[1:4]
shutil.rmtree(work, ignore_errors=True)
os.makedirs(work)
video = os.path.join(work, "plate.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-t", "2", "-c", "copy", video], check=True)
app = QApplication.instance() or QApplication([])
tools = [region, gray, reduce, csv]
doc = D.from_tools(tools, video)
print("wires", [(w.src, w.dst, w.input) for w in doc.wires])
doc.node("region").params.update(region.load_geometry(geometry))
names = [s["name"] for s in doc.node("region").params["shapes"]]
doc.node("region").params["choice"] = names[0]
doc.display = "gray"
D.save(doc, os.path.join(work, "doc.json"))
win = PlayerWindow(os.path.join(work, "doc.json"), "t", tools)


def spin(until, what, limit=12.0):
    t = time.perf_counter()
    while not until():
        if time.perf_counter() - t > limit:
            raise TimeoutError(what)
        app.processEvents()
        time.sleep(0.01)


def shown():
    spin(lambda: win.graph.peek(win.row) is not None, "a shown row")
    return win.graph.peek(win.row).shape


try:
    spin(lambda: win.display._pix is not None, "the first frame")
    g, card = win.graph, win.pane.widget("region")
    print("shapes", names, "choice", doc.node("region").params["choice"], "| plate", doc.node("region").params["plate"])
    live_key, live_shape = g.key("gray"), shown()
    assert g.entry("region").file is None and win.canvas.served == set()
    print("live: gray", live_shape, "key", live_key, "| csv writes beside", win.pane.widget("csv").footage)

    t = time.perf_counter()
    card.button.click()
    assert card.cut is not None, card.status.text()
    spin(lambda: card.cut is None, "the cut")
    print(f"cut in {time.perf_counter() - t:.1f} s:", card.status.text())
    path, print_ = g.entry("region").file
    assert os.path.isfile(path) and win.canvas.served == {"region"} and g.standing("region") == ""
    assert g.key("region") == base_key(footage_print(path), "bgr")
    alone = Graph(D.from_tools([gray, reduce], path), Decoder(path), {t.NAME: t for t in tools})
    assert alone.key("gray") == g.key("gray") != live_key and alone.key("reduce") == g.key("reduce")
    assert shown() == live_shape == alone.compute("gray", win.row).shape
    alone.close()
    alone.decoder.close()
    assert win.pane.widget("csv").footage == path and win.pane.widget("region").video == video
    print("served:", os.path.relpath(path, work), "gray key", g.key("gray"), "= a document's opened on the clip; csv writes beside", os.path.relpath(win.pane.widget("csv").footage, work))
    reads = g.readers.held(path).reads
    plate_reads = g.decoder.reads
    win.goto(30, commit=True)
    spin(lambda: g.peek(30) is not None, "row 30")
    print("a scrub to row 30: clip reads", g.readers.held(path).reads - reads, "plate reads", g.decoder.reads - plate_reads)

    card.set_params({**card.params(), "quality": "lossless"})
    t = time.perf_counter()
    card.button.click()
    spin(lambda: card.cut is None, "the second cut")
    print(f"cut again over the served clip in {time.perf_counter() - t:.1f} s:", card.status.text())
    assert card.status.text().startswith("cut ") and g.entry("region").file is not None and shown() == live_shape

    win._picked("region", {"choice": names[-1]})
    spin(lambda: g.entry("region").file is not None and g.entry("region").file[0] != path, "the other shape's clip")
    print("chose", names[-1], "->", os.path.basename(g.entry("region").file[0]), shown())
    win._picked("region", {"choice": ""})
    app.processEvents()
    assert g.entry("region").file is None and win.canvas.served == set()
    print("no choice: live,", shown())
    moved = [dict(s) for s in doc.node("region").params["shapes"]]
    first = moved[0]
    if "circle" in first:
        first["circle"] = [first["circle"][0] - 4, first["circle"][1], first["circle"][2]]
    else:
        first["polygon"] = [[x - 4, y] for x, y in first["polygon"]]
    win._picked("region", {"choice": names[0], "shapes": moved})
    app.processEvents()
    assert g.entry("region").file is None
    print("a shape moved since the cut: live,", shown())
    print("ok")
finally:
    win.ask_unsaved = lambda: "discard"     # the document was edited above, and offscreen nobody answers the dialog
    win.close()
