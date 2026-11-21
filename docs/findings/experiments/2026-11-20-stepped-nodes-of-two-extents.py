"""The one-off of docs/spec/a-cut-in-time.md's box of the stepped nodes of one extent walked together
over it and those of another apart over theirs: over the crossings clip, `count` and `size` read
`blobs` above a `period` fed `count`'s gate, and `track`, with `travel` below it, reads a second
`blobs` of the same params below the `period`, which reads `threshold`, a `period` cutting a plane; the worker's clip walk run alone, and the rows each node was stepped over, as the probe's
"step" events say, against the clip's rows for the nodes above and each period's for those below.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-stepped-nodes-of-two-extents.py 2>NUL

The gate is `count`'s over the clip as a held run would hand it, made here first; the band is that
of 2026-11-20-a-period-fed-a-gate.py. Qt runs offscreen, so no window opens, and the worker's turns are taken on this thread.
"""
import os
import sys
import threading
import time
import traceback

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder, EndOfStream  # noqa: E402
from sieve_player.graph import Cancelled, Graph, Series, gated  # noqa: E402
from sieve_player.registry import computed, defaults, discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")


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


if __name__ == "__main__":
    decmod.QUIET = True
    app = QApplication([])
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    n, fps = g.count, g.fps
    blobs = np.empty(n, object)
    blobs[:] = [g.compute("blobs", r) for r in range(n)]
    g.close()
    g.decoder.close()
    count = tools["count"]
    result = count.run(Series(blobs, "k", 0, fps), computed(count, defaults(count)))
    band = (float(np.median(result["signal"])), float(np.max(result["signal"])))
    doc.node("count").band = band
    period = doc.add_node("period", (0.0, 0.0), defaults(tools["period"])).id
    below = doc.add_node("blobs", (0.0, 0.0), dict(doc.node("blobs").params)).id
    doc.disconnect("track", "in")
    doc.connect("threshold", period)
    doc.connect(period, below)
    doc.connect(below, "track")
    doc.connect("count", period, "gate")

    def held(nid, key, within):
        return gated({**result, "key": key}, band, "signal")[0] if within.extent.rows is None else None

    g = Graph(doc, Decoder(doc.video), tools, cut_result=held)
    p = g.snapshot()
    (walk,) = p.timed
    cuts = [c.extent.rows for c in walk.cuts]
    print(f"{n} rows; the chain {p.chain}, walked from {p.walk}; below {period}, {walk.chain} over {len(cuts)} periods")
    print(f"track's standing: {p.entries['track'].standing!r}")

    stepped, begun, ready, clip = {}, [], [], []

    def on_event(ev):
        if ev.kind == "step" and ev.lane == "clip":
            stepped.setdefault(ev.node, []).append(ev.row)
        elif ev.kind == "begin" and ev.lane == "clip":
            begun.append((ev.row, ev.length))

    g.on_event = on_event
    w = Worker(g, every=1 << 30)
    w.periodReady.connect(lambda r, s, f: ready.append((r, s)), Qt.DirectConnection)
    w.clipReady.connect(lambda r, s, f: clip.append((r, s)), Qt.DirectConnection)
    w.walk_clip()
    t0 = time.perf_counter()
    turned(w)
    g.close()
    print(f"walked in {time.perf_counter() - t0:.1f} s; {len(begun)} ranges begun on the clip lane, {len(ready)} periods ready")

    every = list(range(n))
    within = [r for a, b in cuts for r in range(a, b)]
    for nid in ("count", "size"):
        print(f"{nid:<6} stepped over the clip's rows once each, in order: {stepped.get(nid) == every}")
    for nid in ("track", "travel"):
        print(f"{nid:<6} stepped over each period's rows alone, in order: {stepped.get(nid) == within}; "
              f"over a row outside every period: {sorted(set(stepped.get(nid, [])) - set(within))[:5] or 'none'}")
    print(f"the ranges begun: the clip's {begun[0] == (0, n)}, then each period's: {begun[1:] == [(a, b - a) for a, b in cuts]}")
    print(f"the clip's result holds {sorted(clip[-1][0]) if clip else None}")
    good = [s == a and set(r) == set(walk.chain) and all(len(r[x]['signal']) == b - a for x in r) for (r, s), (a, b) in zip(ready, cuts)]
    print(f"each period's result begins at its first row, is of {walk.chain} and its rows alone: {all(good) and len(good) == len(cuts)}")
    print("first five periods:", cuts[:5])
