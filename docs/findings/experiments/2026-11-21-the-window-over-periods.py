"""The one-off of docs/spec/a-cut-in-time.md's window box: over the crossings clip, purb's document
with a `period` fed three periods on the video and everything of it below the `period`, then with
`motion` and then `background` below it, each reduced, in place of `blobs`. A Worker's
turns are taken on this thread with no window, event loop or timer. The clip lane walks each period
alone, and those walks are the truth. Then each window below is walked over a held.Runs holding
the first period's walk alone: what heldwalks.window_periods and windowPeriodReady give each period
it overlaps is set against that period's own walk at the same rows, node by node. A node the window
says is best effort is set against the walk all the same, and its differing rows are counted.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-21-the-window-over-periods.py 2>NUL
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
from sieve_player.heldwalks import held_periods, period_run, window_periods  # noqa: E402
from sieve_player.registry import defaults, discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
PERIODS = [("a", 40, 200), ("b", 180, 330), ("c", 400, 550)]
WINDOWS = [(150, 200), (300, 200), (100, 50)]   # a cut short before and b inside; b cut short before and c after; inside a alone
TURNS = 20_000


def document(tools, folder, frame):
    doc = D.load(DOC, tools)
    path = os.path.join(folder, "periods.json")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"rows": 590, "periods": [{"name": n, "first": a, "end": b} for n, a, b in PERIODS]}, f)
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


def turned(w, g):
    for turns in range(TURNS):
        with w._cv:
            turn = w._turn()
        if turn is None:
            return turns
        serves, steps = turn
        for job, act in steps:
            g.serving(serves, job.name)
            act()
    raise RuntimeError(f"still turning after {TURNS} turns")


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


def differing(got, truth, offset):
    """The rows, of the footage's from `offset`, at which `got` differs from `truth` cut there."""
    fields = [f for f in ("signal", "rows") if f in got and f in truth]
    n = len(got[fields[0]])
    return [offset + i for i in range(n) if any(not equal(got[f][i], truth[f][offset - truth_start[0] + i]) for f in fields)]


if __name__ == "__main__":
    decmod.QUIET = True
    t0 = time.perf_counter()
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    for frame in (None, "motion", "background"):
        print(f"below the period: {frame or 'blobs and what reads it'}")
        with tempfile.TemporaryDirectory() as tmp:
            doc = document(tools, tmp, frame)
            g = Graph(doc, Decoder(doc.video), tools)
            w = Worker(g, tell_every=3600.0)
            p = g.snapshot()
            (timed,) = p.timed
            print("  the chain and its reach:", ", ".join(f"{nid} {p.entries[nid].reach}" for nid in timed.chain))

            truth, runs = {}, held.Runs(1 << 40, lambda nid, r: 0)

            def period_ready(results, start, of, fps):
                run = period_run(g.snapshot(), results, start, of)
                if run is not None:
                    truth[run[4]] = (start, run[2])
                    if run[4] == (PERIODS[0][1], PERIODS[0][2]):
                        s, rows, has, chain, cut, stack = run
                        runs.hold(s, rows, has, chain, cut, walked=stack)
            w.periodReady.connect(period_ready)
            w.walk_clip()
            turns = turned(w, g)
            w.stop_clip()
            turned(w, g)
            print(f"each period walked alone by the clip lane: {sorted(truth)}, {turns} turns, {time.perf_counter() - t0:.1f} s; the first held")
            w.give_periods(held_periods(p, runs))

            for s, n in WINDOWS:
                shown = window_periods(p, runs, s, n)

                def ready(results, start, of, fps, shown=shown):
                    got = shown.get(of)
                    if got is not None and not got[3] and got[0] == start:
                        shown[of] = (start, results, got[2], False)
                w.windowPeriodReady.connect(ready)
                t = time.perf_counter()
                w.set_window(s, n)
                turns = turned(w, g)
                w.windowPeriodReady.disconnect(ready)
                print(f"window {s}-{s + n}: {turns} turns, {time.perf_counter() - t:.1f} s")
                for (src, c), (start, results, best, was_held) in sorted(shown.items(), key=lambda kv: kv[0][1].extent.rows):
                    rows = c.extent.rows
                    truth_start = [truth[rows][0]]
                    said = "held" if was_held else f"walked {start}-{start + len(next(iter(results.values()))['signal']) if results else start}"
                    print(f"  period {rows}: {said}; best effort: {', '.join(sorted(best)) or 'none'}")
                    for nid in timed.chain:
                        r = results.get(nid)
                        if not isinstance(r, dict) or "signal" not in r:
                            print(f"    {nid:<10} no result")
                            continue
                        bad = differing(r, truth[rows][1][nid], start)
                        inside = [row for row in bad if s <= row < s + n]
                        mark = "best effort" if nid in best else "exact"
                        print(f"    {nid:<10} {mark:<11} {len(r['signal']):>4} rows from {start}; differ from its period's walk at "
                              f"{len(bad)} rows, {len(inside)} inside the window{': ' + str(inside[:6]) if inside else ''}")
    print(f"{time.perf_counter() - t0:.1f} s")
