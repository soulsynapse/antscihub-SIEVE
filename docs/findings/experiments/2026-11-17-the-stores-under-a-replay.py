"""The stores of a tree's Graph under one thread's replay of what the player does, the same asks in
the same order whichever tree: the display looping a window of <window rows>, then a clip walk of
<walk rows> under it, a display row to four of the walk's, then the window moved into rows the
walk passed. Counted: the tools' runs and the decodes, by who asked, each store's discards, and the
memo's bytes as it counts them and as they are. <tree> is a checkout of the repository, this one
or another commit's (`git archive <commit> | tar -x -C <dir>`). [shown] puts the display flag on
that node, and [moved to] is the row the window is moved to, the middle of the walked rows with none. The limits are MB.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-the-stores-under-a-replay.py <tree> <document> <out.json> <memo MB> <cache MB> <window rows> <walk rows> [shown [moved to]]"""
import json
import os
import sys
import time

tree, docpath, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]), os.path.abspath(sys.argv[3])
MEMO, CACHE, W, L = int(sys.argv[4]) << 20, int(sys.argv[5]) << 20, int(sys.argv[6]), int(sys.argv[7])
SHOWN = sys.argv[8] if len(sys.argv) > 8 else None
MOVED = int(sys.argv[9]) if len(sys.argv) > 9 else None
sys.path.insert(0, tree)
os.chdir(tree)

import numpy as np
import psutil

import sieve_player
from sieve_player import document
from sieve_player.decoder import Decoder
from sieve_player.graph import Graph
from sieve_player.registry import discover

assert os.path.abspath(sieve_player.__file__).startswith(os.path.abspath(tree)), sieve_player.__file__
PROC = psutil.Process()
who = ["-"]
runs = {}


def counted(name, run):
    def inner(frames, row, params):
        k = (who[0], name)
        runs[k] = runs.get(k, 0) + 1
        return run(frames, row, params)
    return inner


tools = {e.name: e.module for e in discover("tools") if e.ok}
doc = document.load(docpath, tools)
if SHOWN:
    doc.display = SHOWN
for n in doc.nodes:
    t = tools.get(n.tool)
    if t is not None and getattr(t, "KIND", "frame") != "series" and not getattr(t.run, "_counted", False) and hasattr(t, "run"):
        t.run = counted(t.NAME, t.run)
        t.run._counted = True
video, _ = document.pick_path(doc, tools, document.VIDEO_TOOL)
video = video or doc.video_path()


def deep(v):
    if isinstance(v, np.ndarray):
        if v.dtype.names:
            return v.nbytes + sum(deep(x) for n in v.dtype.names if v.dtype[n] == object for x in v[n].ravel())
        if v.dtype == object:
            return v.nbytes + sum(deep(x) for x in v.ravel())
        return v.nbytes
    return 0 if v is None else 64


def memo_deep(m):
    with m._lock:
        vals = list(m._big.values()) + list(m._small.values()) + [v for _, v in m._pinned.values()]
    return sum(deep(v) for v in vals)


def fresh():
    g = Graph(doc, Decoder(video, cache_bytes=CACHE), tools, memo_bytes=MEMO)
    g.sync()
    p = g.snapshot()
    draws = [nid for nid, e in p.entries.items() if e.kind == "frame" and e.fed and hasattr(e.tool, "draw")]
    if hasattr(g, "paints"):
        g.paints(draws)
    return g, p


def decoders(g):
    return [g.decoder, *g.readers.decoders()]


def snap(g):
    ds = decoders(g)
    return {"runs display": sum(v for (w, _), v in runs.items() if w == "display"),
            "runs walk": sum(v for (w, _), v in runs.items() if w == "walk"),
            "decodes": sum(d.decodes for d in ds), "seeks": sum(d.seeks for d in ds),
            "cache discards": sum(getattr(d, "evictions", 0) for d in ds),
            "memo discards": g.memo.evictions, "memo hits": g.memo.hits, "memo misses": g.memo.misses}


def since(g, a):
    b = snap(g)
    return {k: b[k] - a[k] for k in b}


dec = {"display": 0, "walk": 0}


def show(g, p, row):
    who[0] = "display"
    if hasattr(g, "looks_at"):
        g.looks_at(row)
    g.serving("scrub", "scrub")
    before = sum(d.decodes for d in decoders(g))
    with g.scrubbing():
        g.compute(p.shown, row, p=p)
        if p.over is not None:
            g.compute(p.over, row, p=p)
        for nid in g.drawing(p):
            g.compute(nid, row, p=p)
    dec["display"] += sum(d.decodes for d in decoders(g)) - before


def walk(g, p, row):
    who[0] = "walk"
    g.serving("walk", "clip")
    before = sum(d.decodes for d in decoders(g))
    g.walk_row(row, p)
    dec["walk"] += sum(d.decodes for d in decoders(g)) - before


def holds(g, start, rows):
    if hasattr(g, "holds"):
        g.holds(start, rows)


def lap(g, p, start, rows):
    a, d0 = snap(g), dec["display"]
    for r in range(start, start + rows):
        show(g, p, r)
    s = since(g, a)
    return {"tool runs": s["runs display"], "decodes": dec["display"] - d0, "memo discards": s["memo discards"], "cache discards": s["cache discards"]}


res = {"tree": os.path.basename(tree), "doc": os.path.basename(docpath), "memo MB": MEMO >> 20, "cache MB": CACHE >> 20, "window": W, "walk": L}
g, p = fresh()
L = min(L, g.count)
res["shown"], res["walked node"], res["drawing"] = p.shown, p.walk, list(g.drawing(p))

# A: the display loops the window, three laps, nothing else running
holds(g, 0, W)
res["A loop alone"] = [lap(g, p, 0, W) for _ in range(3)]
res["A memo MB counted / deep"] = [round(g.memo.bytes / 2**20, 2), round(memo_deep(g.memo) / 2**20, 2)]
res["A cache MB"] = round(g.decoder.cache_bytes / 2**20, 2)
g.close()

# B: one lap, then a clip walk of L rows with the display going on round the window, a row to four of the walk's
runs.clear()
dec["display"] = dec["walk"] = 0
g, p = fresh()
holds(g, 0, W)
lap(g, p, 0, W)
a, d0, w0 = snap(g), dec["display"], dec["walk"]
at, t_walk, t_show, peak, peak_deep, shown_rows = 0, 0.0, 0.0, 0, 0, 0
for r in range(L):
    t = time.perf_counter()
    walk(g, p, r)
    t_walk += time.perf_counter() - t
    if r % 4 == 3:
        at = (at + 1) % W
        t = time.perf_counter()
        show(g, p, at)
        t_show += time.perf_counter() - t
        shown_rows += 1
    if r % 50 == 49:
        peak = max(peak, g.memo.bytes)
        peak_deep = max(peak_deep, memo_deep(g.memo))
if hasattr(g, "rests"):
    g.serving("walk", "clip")
    g.rests()      # as the walk says at its last row
s = since(g, a)
res["B walk under a looping display"] = {
    "walked": L, "display rows asked": shown_rows,
    "display: tool runs again": s["runs display"], "display: decodes again": dec["display"] - d0,
    "walk: tool runs": s["runs walk"], "walk: decodes": dec["walk"] - w0, "walk: decodes a row": round((dec["walk"] - w0) / L, 3),
    "seeks": s["seeks"], "memo discards": s["memo discards"], "cache discards": s["cache discards"],
    "walk ms a row": round(1000 * t_walk / L, 3), "display ms a row": round(1000 * t_show / max(1, shown_rows), 3),
    "memo peak MB counted / deep": [round(peak / 2**20, 2), round(peak_deep / 2**20, 2)],
    "runs by tool": {f"{w} {n}": v for (w, n), v in sorted(runs.items())}}

# C: the window moved to rows the walk passed, two laps
M = L // 2 if MOVED is None else MOVED
holds(g, M, W)
res[f"C window moved to row {M}"] = [lap(g, p, M, min(W, g.count - M)) for _ in range(2)]
res["rss MB"] = round(PROC.memory_info().rss / 2**20)
g.close()
with open(out, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=1)
