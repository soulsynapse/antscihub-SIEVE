"""The one-offs of docs/spec/a-cut-in-time.md's Rows below a cut are the footage's, over the crossings
clip: a tracks csv below a `period` against the same node's above it, row for row; `background`
below a `period` of two periods against the composite of each period written to a lossless clip of
its own and run there; and a node below a `region`, cut from the plate and served, against the
plate's rows.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-rows-below-a-cut-are-the-footages.py 2>NUL

The periods are this script's. A track's ids are of where its walk began, so the csvs are compared
by row and centroid and not by id. The served clip is an FFV1 crop of the plate this script writes
to a folder of its own, put in place of the store's by `region.cut_file`, so no clip is cut into the
store. Qt runs offscreen, so no window opens, and the worker's turns are taken on this thread.
"""
import csv as csvmod
import io
import os
import sys
import tempfile
import threading
import time
import traceback

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder, EndOfStream  # noqa: E402
from sieve_player.graph import Cancelled, Graph  # noqa: E402
from sieve_player.registry import defaults, discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
GEOMETRY = os.path.join(ROOT, "video-tests", "00000_168-178.shapes.geometry.json")
PERIODS = [(100, 160), (140, 200)]
BACKGROUND = [(20, 120), (300, 460)]


TURNS = 1_000_000


def turned(w, between=None):
    """Takes the Worker `w`'s turns on this thread, as its loop takes them, until no rung is due,
    calling `between` after each; the turns taken."""
    threading.current_thread().name = "worker"     # as Worker.run names its thread: the probe and Readers.reap read it
    for turns in range(TURNS):
        with w._cv:
            turn = w._turn()
        if turn is None:
            return turns
        serves, steps = turn
        w.graph.readers.reap()
        job = None
        try:
            for job, act in steps:
                w.graph.serving(serves, job.name)
                act()
        except Cancelled:
            job.cancelled()
        except EndOfStream:
            w.shortened.emit(w.graph.count)
            job.ended()
        except Exception as e:
            traceback.print_exc()
            job.raised(e)
        if between is not None:
            between()
    raise RuntimeError(f"still turning after {TURNS} turns")


def filed(doc, tools, nid, rows, n, folder):
    name = f"{nid}.json"
    with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(tools["period"].periods_text(n, rows))
    selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": folder, "pattern": name})
    doc.connect(selector.id, nid, "periods")
    doc.node(nid).params.update(tools["period"].PATHS["periods"](D.pick_path(doc, tools, nid, "periods")[0]))


def walked(g):
    """The clip's result and every period's, [(start, result)], as the clip lane walks them."""
    ready, clip = [], []
    w = Worker(g, every=1 << 30)
    w.periodReady.connect(lambda r, s, f: ready.append((s, r)), Qt.DirectConnection)
    w.clipReady.connect(lambda r, s, f: clip.append(r), Qt.DirectConnection)
    w.walk_clip()
    want = sum(len(t.cuts) for t in g.snapshot().timed)
    t0 = time.perf_counter()
    turned(w)
    return clip[-1] if clip else None, ready


def records(text):
    """{row: sorted (cx, cy)} of a tracks csv's lines."""
    out = {}
    for line in csvmod.DictReader(io.StringIO("".join(text.splitlines(True)[1:]))):
        out.setdefault(int(line["row"]), []).append((round(float(line["cx"]), 3), round(float(line["cy"]), 3)))
    return {r: sorted(v) for r, v in out.items()}


def written(path, frames):
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"FFV1"), 30.0, frames[0].shape[1::-1], False)
    for f in frames:
        w.write(f)
    w.release()


if __name__ == "__main__":
    decmod.QUIET = True
    app = QApplication([])
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    folder = tempfile.mkdtemp()
    t_all = time.perf_counter()

    doc = D.load(DOC, tools)
    n = Graph(doc, Decoder(doc.video), tools).count
    period = doc.add_node("period", (0.0, 0.0), defaults(tools["period"])).id
    filed(doc, tools, period, PERIODS, n, folder)
    blobs = doc.add_node("blobs", (0.0, 0.0), dict(doc.node("blobs").params)).id
    track = doc.add_node("track", (0.0, 0.0), dict(doc.node("track").params)).id
    doc.connect("threshold", period)
    doc.connect(period, blobs)
    doc.connect(blobs, track)
    g = Graph(doc, Decoder(doc.video), tools)
    e = g.snapshot().entries
    print(f"{n} rows. {track} below {period} keyed as track above it: {e[track].key == e['track'].key}; "
          f"{blobs} as blobs: {e[blobs].key == e['blobs'].key}")
    whole, ready = walked(g)
    g.close()
    csv = tools["csv"]
    above = records(csv.text(whole["track"], 0, g.fps, doc.video))
    for start, result in ready:
        length = len(result[track]["rows"])
        rows = records(csv.text(result[track], start, g.fps, doc.video))
        span = (start, start + length)
        inside = set(rows) <= set(range(*span))
        same = {r: v for r, v in above.items() if span[0] <= r < span[1]} == rows
        print(f"period {span}: the csv's rows the footage's and inside it: {inside}, {len(rows)} rows with records; "
              f"each row's records the same as track's above it: {same}")

    doc = D.load(DOC, tools)
    period = doc.add_node("period", (0.0, 0.0), defaults(tools["period"])).id
    filed(doc, tools, period, BACKGROUND, n, folder)
    bg = doc.add_node("background", (0.0, 0.0), defaults(tools["background"])).id
    doc.connect("video", period)
    doc.connect(period, bg)
    g = Graph(doc, Decoder(doc.video), tools)
    cuts = g.snapshot().entries[bg].cuts
    composites = [g.compute(bg, c.extent.rows[0] + 1, cut=c) for c in cuts]
    plate = [g.compute("video", r) for r in range(max(b for _, b in BACKGROUND))]
    g.close()
    for c, below in zip(cuts, composites):
        a, b = c.extent.rows
        clip = os.path.join(folder, f"period_{a}-{b}.avi")
        written(clip, plate[a:b])
        alone = D.load(DOC, tools)
        alone.video = clip
        alone.node("video").params["scale"] = 1.0
        node = alone.add_node("background", (0.0, 0.0), defaults(tools["background"])).id
        alone.connect("video", node)
        h = Graph(alone, Decoder(clip), tools)
        lossless = h.count == b - a and all(np.array_equal(h.compute("video", r), plate[a + r]) for r in range(b - a))
        there = h.compute(node, 0)
        h.close()
        h.decoder.close()
        print(f"background over {(a, b)}: the clip's {b - a} rows the plate's byte for byte: {lossless}; "
              f"the composite below the period the clip's: {np.array_equal(below, there)}; "
              f"and not the other period's: {not np.array_equal(below, composites[1 - cuts.index(c)])}")

    region = {**defaults(tools["region"]), **tools["region"].load_geometry(GEOMETRY), "choice": "diamond"}
    y0, y1, x0, x1 = tools["region"].served(region)
    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    served = os.path.join(folder, "diamond.avi")
    written(served, [np.ascontiguousarray(g.compute("video", r)[y0:y1, x0:x1]) for r in range(n)])
    g.close()
    tools["region"].cut_file = lambda video, footage, params: served if params["serve clip"] else None
    for serve in (False, True):
        doc = D.load(DOC, tools)
        cut = doc.add_node("region", (0.0, 0.0), {**region, "serve clip": serve}).id
        thr = doc.add_node("threshold", (0.0, 0.0), dict(doc.node("threshold").params)).id
        on_plate = doc.add_node("threshold", (0.0, 0.0), dict(doc.node("threshold").params)).id
        doc.connect("video", cut)
        doc.connect(cut, thr)
        doc.connect("video", on_plate)
        g = Graph(doc, Decoder(doc.video), tools)
        is_served = g.snapshot().entries[cut].file is not None
        rows = [10, 250, n - 1]
        same = all(np.array_equal(g.compute(thr, r), g.compute(on_plate, r)[y0:y1, x0:x1]) for r in rows)
        apart = not any(np.array_equal(g.compute(cut, r), g.compute("video", r + 1)[y0:y1, x0:x1]) for r in rows[:-1])
        g.close()
        print(f"threshold below a region {'served' if is_served else 'cut from the plate'}: at rows {rows} the plate's "
              f"threshold cut to the rect: {same}; the region's frame at a row not the plate's a row later: {apart}")
    print(f"in {time.perf_counter() - t_all:.1f} s")
