"""The one-off of docs/spec/a-cut-in-time.md's box of a period held not walked again: over the
crossings clip, purb's document with a `period` fed three periods on the video, everything of it
below the `period`, and beside `blobs` a `motion` and a `background` each reduced. A Worker's turns
are taken on this thread, its periods held in a held.Runs by `heldwalks.period_run` and told back by
`heldwalks.held_periods` as the window does, with no window, event loop or timer. The runs are written and
read back through held.File; the document's first period then begins later and its last ends
later, a new Graph with no memo walks the clip again over the runs read back, and the rows each
node was stepped over and computed at are set against the periods that moved. Last the moved
document is walked with an empty held.Runs, and every period's result is set against the one
reached over the runs.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-a-period-held-not-walked-again.py 2>NUL
"""
import json
import os
import sys
import tempfile
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import held  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import defaults, discover  # noqa: E402
from sieve_player.heldwalks import held_chain, held_periods, period_run  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
BEFORE = [("a", 40, 200), ("b", 180, 330), ("c", 400, 550)]
AFTER = [("a", 60, 200), ("b", 180, 330), ("c", 400, 590)]       # a's first row moved, c's last row moved later
TURNS = 20_000


def document(tools, folder, periods, frame):
    """purb's document with a `period` on the video fed `periods`; below it `blobs` and what reads
    it for a `frame` of None, else `frame` and a `reduce` of it, `blobs` then fed nothing."""
    doc = D.load(DOC, tools)
    path = os.path.join(folder, "periods.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"rows": 590, "periods": [{"name": n, "first": a, "end": b} for n, a, b in periods]}, f)
    period = doc.add_node("period", (0.0, 0.0), {**defaults(tools["period"]), **tools["period"].load_periods(path)}).id
    selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": folder, "pattern": "periods.json"}).id
    doc.connect(selector, period, "periods")
    doc.disconnect("threshold", "in")
    doc.connect("video", period)
    if frame is None:
        doc.connect(period, "threshold")
    else:
        f = doc.add_node(frame, (0.0, 0.0), defaults(tools[frame])).id
        r = doc.add_node("reduce", (0.0, 0.0), defaults(tools["reduce"])).id
        doc.connect(period, f)
        doc.connect(f, r)
    return doc


def walked(doc, tools, runs):
    """The clip walked by a Worker whose turns are taken here, each period it walks held in `runs`
    as the window holds it: the Graph, the clip lane's (node, kind) -> rows, and the turns it took."""
    g = Graph(doc, Decoder(doc.video), tools)
    w = Worker(g, tell_every=3600.0)

    def ready(results, start, fps):
        if (run := period_run(g.snapshot(), results, start, g.count)) is not None:
            start, rows, has, chain, cut, stack = run
            runs.hold(start, rows, has, chain, cut, walked=stack)
        w.give_periods(held_periods(g.snapshot(), runs, g.count))
    w.periodReady.connect(ready)
    w.give_periods(held_periods(g.snapshot(), runs, g.count))
    seen = {}

    def on_event(ev):
        if ev.lane == "clip" and ev.kind in ("run", "step"):
            seen.setdefault((ev.node, ev.kind), []).append(ev.row)
    g.on_event = on_event
    w.walk_clip()
    for turns in range(TURNS):
        with w._cv:
            turn = w._turn()
        if turn is None:
            break
        serves, steps = turn
        for job, act in steps:
            g.serving(serves, job.name)
            act()
    else:
        print(f"  still turning after {TURNS} turns")
    return g, seen, turns


def results(g, runs):
    """(chain node, period rows) -> that node's result over the period, as `runs` list it."""
    out, p = {}, g.snapshot()
    for w in p.timed:
        chain = held_chain(p, w.chain)
        for nid in w.chain:
            for c in p.entries[nid].cuts:
                parts = runs.listed(nid, chain, c, g.count).parts
                if parts:
                    out[(nid, c.extent.rows)] = {f: np.concatenate([r[f] for _, r in parts]) for f in ("signal", "rows") if f in parts[0][1]}
    return out


def equal(x, y):
    """Whether two values of a row are the same, a table's fields and an object's items each."""
    if x is None or y is None:
        return x is y
    x, y = np.asarray(x), np.asarray(y)
    if x.shape != y.shape or x.dtype.names != y.dtype.names:
        return False
    if x.dtype.names:
        return all(equal(x[f], y[f]) for f in x.dtype.names)
    if x.dtype == object:
        return all(equal(a, b) for a, b in zip(x.ravel(), y.ravel()))
    return bool(np.array_equal(x, y, equal_nan=x.dtype.kind in "fc"))


def differ(a, b):
    """The rows at which two results over one period differ."""
    if len(a["signal"]) != len(b["signal"]):
        return ["length"]
    return [i for i in range(len(a["signal"])) if any(not equal(a[f][i], b[f][i]) for f in a if f in b)]


if __name__ == "__main__":
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    size = lambda nid, r: 0
    moved = {r for p in AFTER if p not in BEFORE for r in range(p[1], p[2])}
    print(f"before {BEFORE}, after {AFTER}")
    for frame in (None, "motion", "background"):
        print(f"below the period: {frame or 'blobs, track and what reads them'}")
        with tempfile.TemporaryDirectory() as tmp:
            t = time.perf_counter()
            runs = held.Runs(1 << 40, size)
            g, seen, turns = walked(document(tools, tmp, BEFORE, frame), tools, runs)
            cut_runs = [r for r in runs if r.cut]
            path = os.path.join(tmp, "doc.json.series")
            held.File(path).write(runs.all)
            again = held.Runs(1 << 40, size)
            again.take(held.File(path).load())
            print(f"  before: {turns} turns, {time.perf_counter() - t:.1f} s; {len(cut_runs)} runs of a cut, "
                  f"{sum(1 for r in cut_runs if r.walked)} holding walked rows; written and read back, {len(again)} runs, {os.path.getsize(path)} bytes")

            t = time.perf_counter()
            g, seen, turns = walked(document(tools, tmp, AFTER, frame), tools, again)
            print(f"  after, over the runs read back: {turns} turns, {time.perf_counter() - t:.1f} s")
            for (nid, kind), rows in sorted(seen.items()):
                outside = sorted(set(rows) - moved)
                print(f"    {nid:<10} {kind:<4} {len(rows):>4} rows, {min(rows)}-{max(rows)}; outside the moved periods: {outside[:6] or 'none'}")
            reached = results(g, again)

            t = time.perf_counter()
            scratch = held.Runs(1 << 40, size)
            g, _, turns = walked(document(tools, tmp, AFTER, frame), tools, scratch)
            truth = results(g, scratch)
            bad = {k: differ(reached[k], truth[k]) for k in truth if k in reached}
            print(f"  from an empty held.Runs and no memo: {turns} turns, {time.perf_counter() - t:.1f} s; {len(truth)} results a node a period, "
                  f"equal to those reached: {not any(bad.values()) and set(reached) == set(truth)}")
            for k in sorted(set(truth) ^ set(reached)):
                print(f"    {k}: in {'the walk from scratch' if k in truth else 'the walk over the runs'} alone")
            for k, v in sorted(bad.items()):
                if v:
                    print(f"    {k}: rows differ {v[:8]}{' ...' if len(v) > 8 else ''}")
