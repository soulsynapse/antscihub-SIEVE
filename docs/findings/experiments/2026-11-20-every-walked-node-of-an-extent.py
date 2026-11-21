"""The one-off of docs/spec/a-cut-in-time.md's box of every series node of one extent walked: over
the crossings clip, purb's document with a `motion` and a `reduce` of it beside `threshold`, reading
what `threshold` reads, so `track` on `blobs` and `reduce` on `motion` are two walked nodes of one
extent; and the same below a `period` of three periods on the video. A Worker's turns are taken on
this thread, no window, event loop or timer. Each node's rows stepped once a walk, the video's rows
read at each row as often as with `track` alone, and each node's result against the same node walked in a document of its branch
alone.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-every-walked-node-of-an-extent.py 2>NUL
"""
import json
import os
import sys
import tempfile
import time
from collections import Counter

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import held  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.heldwalks import held_chain, held_periods, period_run  # noqa: E402
from sieve_player.registry import defaults, discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
PERIODS = [("a", 40, 200), ("b", 180, 330), ("c", 400, 550)]
TURNS = 20_000


def document(tools, folder, branches, cut):
    """purb's document, `branches` of "track" and "motion" kept, below a `period` of PERIODS where
    `cut`, else on what `threshold` reads."""
    doc = D.load(DOC, tools)
    above = doc.source("threshold", "in").src
    if cut:
        path = os.path.join(folder, "periods.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"rows": 590, "periods": [{"name": n, "first": a, "end": b} for n, a, b in PERIODS]}, f)
        period = doc.add_node("period", (0.0, 0.0), {**defaults(tools["period"]), **tools["period"].load_periods(path)}).id
        selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": folder, "pattern": "periods.json"}).id
        doc.connect(selector, period, "periods")
        doc.connect("video", period)
        above = period
    doc.disconnect("threshold", "in")
    if "track" in branches:
        doc.connect(above, "threshold")
    if "motion" in branches:
        doc.add_node("motion", (0.0, 0.0), defaults(tools["motion"]))
        doc.add_node("reduce", (0.0, 0.0), defaults(tools["reduce"]))
        doc.connect(above, "motion")
        doc.connect("motion", "reduce")
    return doc


def walked(doc, tools):
    """The clip walked by a Worker whose turns are taken here, each period held as the window
    holds it: (node, period rows or None) -> result, the clip lane's (node, kind) -> rows, and
    the video's rows read."""
    g = Graph(doc, Decoder(doc.video), tools)
    runs, clip = held.Runs(1 << 40, lambda nid, r: 0), {}
    w = Worker(g, tell_every=3600.0)

    def ready(results, start, fps):
        if (run := period_run(g.snapshot(), results, start)) is not None:
            start, rows, has, chain, cut, stack = run
            runs.hold(start, rows, has, chain, cut, walked=stack)
        w.give_periods(held_periods(g.snapshot(), runs, g.count))
    w.periodReady.connect(ready)
    w.clipReady.connect(lambda results, start, fps: clip.update(results))
    seen, read = {}, Counter()

    def on_event(ev):
        if ev.lane == "clip" and ev.kind in ("run", "step"):
            seen.setdefault((ev.node, ev.kind), []).append(ev.row)
        if ev.lane == "clip" and ev.kind in ("cache", "decode", "seek"):
            read[ev.row] += 1
    g.on_event = on_event
    w.walk_clip()
    for _ in range(TURNS):
        with w._cv:
            turn = w._turn()
        if turn is None:
            break
        serves, steps = turn
        for job, act in steps:
            g.serving(serves, job.name)
            act()
    p, out = g.snapshot(), {}
    for nid in p.chain:
        if isinstance(clip.get(nid), dict):
            out[(nid, None)] = clip[nid]
    for tw in p.timed:
        chain = held_chain(p, tw.chain)
        for nid in tw.chain:
            for c in p.entries[nid].cuts:
                parts = runs.listed(nid, chain, c, g.count).parts
                if parts:
                    out[(nid, c.extent.rows)] = {f: np.concatenate([r[f] for _, r in parts]) for f in ("signal", "rows") if f in parts[0][1]}
    return p, out, seen, read


def equal(x, y):
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


def same(a, b):
    return len(a["signal"]) == len(b["signal"]) and all(equal(a[f][i], b[f][i]) for f in ("signal", "rows") if f in a and f in b for i in range(len(a["signal"])))


if __name__ == "__main__":
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    for cut in (False, True):
        print(f"{'below a period of ' + str(PERIODS) if cut else 'with no period'}:")
        with tempfile.TemporaryDirectory() as tmp:
            t = time.perf_counter()
            p, both, seen, read = walked(document(tools, tmp, ("track", "motion"), cut), tools)
            print(f"  both branches: {time.perf_counter() - t:.1f} s; walked nodes {[q.walk for tw in ([p] + [p.of(w) for w in p.timed]) for q in tw.parts() if q.chain]}, "
                  f"unrun {p.unrun or 'none'}")
            want = Counter(r for _, a, b in PERIODS for r in range(a, b)) if cut else Counter(range(590))
            stepped = {nid: Counter(rows) for (nid, kind), rows in seen.items() if kind == "step"}
            for nid, rows in sorted(stepped.items()):
                print(f"    {nid:<8} stepped {sum(rows.values())} rows, each once a walk: {rows == want}")
            alone, reads = {}, {}
            for branch in ("track", "motion"):
                _, got, _, reads[branch] = walked(document(tools, tmp, (branch,), cut), tools)
                alone.update(got)
            print(f"    video rows read {sum(read.values())}, at each row as often as with track alone: {read == reads['track']}")
            bad = sorted(k for k in alone if k not in both or not same(both[k], alone[k]))
            print(f"    {len(both)} results a node{' a period' if cut else ''}; each equal to its branch walked alone: {not bad and set(both) == set(alone)}"
                  f"{'; differ: ' + str(bad[:6]) if bad else ''}")
