"""The one-off of docs/spec/a-cut-in-time.md's first box of Outside a cut is absent, over the
crossings clip: a tracks csv below a `period` of two periods that overlap, walked by the clip lane,
its rows against the periods'; and `threshold` and `background` below it asked at rows inside and
outside the periods, of one period and of two.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-outside-a-cut-is-absent.py 2>NUL

The periods are this script's. Qt runs offscreen, so no window opens, and the worker's turns are taken on this thread.
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

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder, EndOfStream  # noqa: E402
from sieve_player.graph import Cancelled, Graph  # noqa: E402
from sieve_player.registry import defaults, discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
PERIODS = [(100, 160), (140, 200)]
ASKED = (50, 120, 150, 300)


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
    name = f"{nid}_{len(rows)}.json"
    with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(tools["period"].periods_text(n, rows))
    selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": folder, "pattern": name})
    doc.connect(selector.id, nid, "periods")
    doc.node(nid).params.update(tools["period"].PATHS["periods"](D.pick_path(doc, tools, nid, "periods")[0]))


def walked(g):
    """Every period's result, [(start, result)], as the clip lane walks them."""
    ready = []
    w = Worker(g, every=1 << 30)
    w.periodReady.connect(lambda r, s, of, f: ready.append((s, r)), Qt.DirectConnection)
    w.walk_clip()
    want = sum(len(t.cuts) for t in g.snapshot().timed)
    t0 = time.perf_counter()
    turned(w)
    return ready


def rows_of(text):
    return {int(line["row"]) for line in csvmod.DictReader(io.StringIO("".join(text.splitlines(True)[1:])))}


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
    csv = doc.add_node("csv", (0.0, 0.0), defaults(tools["csv"])).id
    doc.connect("threshold", period)
    doc.connect(period, blobs)
    doc.connect(blobs, track)
    doc.connect(track, csv)
    g = Graph(doc, Decoder(doc.video), tools)
    ready = walked(g)
    g.close()
    inside = set().union(*(range(a, b) for a, b in PERIODS))
    every = set()
    for start, result in ready:
        span = (start, start + len(result[csv]["rows"]))
        written = rows_of(tools["csv"].text(result[csv], start, g.fps, doc.video))
        every |= written
        print(f"csv below {period}, period {span}: {len(written)} rows with records, rows {min(written)}..{max(written)}, "
              f"each inside the period: {written <= set(range(*span))}")
    print(f"{len(ready)} periods walked of {len(PERIODS)}; rows written outside every period: {sorted(every - inside) or 'none'}")

    for periods in (PERIODS[:1], PERIODS):
        doc = D.load(DOC, tools)
        period = doc.add_node("period", (0.0, 0.0), defaults(tools["period"])).id
        filed(doc, tools, period, periods, n, folder)
        thr = doc.add_node("threshold", (0.0, 0.0), dict(doc.node("threshold").params)).id
        bg = doc.add_node("background", (0.0, 0.0), defaults(tools["background"])).id
        doc.connect("video", period)
        doc.connect(period, thr)
        doc.connect(period, bg)
        g = Graph(doc, Decoder(doc.video), tools)
        for nid in (thr, bg):
            got = {row: g.compute(nid, row) is not None for row in ASKED}
            held = {row: any(c.extent.holds(row) for c in g.snapshot().entries[nid].cuts) for row in ASKED}
            print(f"{doc.node(nid).tool} below periods {periods}: computed at {[r for r, v in got.items() if v]}, "
                  f"absent at {[r for r, v in got.items() if not v]}; the rows a period holds: {got == held}")
        g.close()
    print(f"in {time.perf_counter() - t_all:.1f} s")
