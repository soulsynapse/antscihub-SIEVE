"""The one-off of docs/spec/a-cut-in-time.md's box of cuts nested: over the crossings clip, a `period`
under a `region` and a `region` under a `period`, each with `track` below them, their one extent
and the rows `track` is stepped over; and a `period` under a `period`, the lower fed the gate of a
`count` below the upper, which the clip lane walks over each upper period first, the lower's periods
against the runs that gate keeps inside each upper period, and each a cut of the period it lies in.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-cuts-nested-in-time-and-space.py 2>NUL

The region is `diamond` of video-tests/00000_168-178.shapes.geometry.json, cut from the plate and
never served; its periods and the upper periods are this script's. The band on the gate is `count`'s
median over the clip, as 2026-11-20-a-period-fed-a-gate.py's. Qt runs offscreen, so no window opens.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.cut import made_from  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, Series  # noqa: E402
from sieve_player.registry import computed, defaults, discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
GEOMETRY = os.path.join(ROOT, "video-tests", "00000_168-178.shapes.geometry.json")
PERIODS = [(100, 160), (140, 200)]
UPPER = [(0, 300), (350, 590)]


def filed(doc, tools, nid, rows, n, folder):
    """The `period` `nid` fed a file of `rows` by a `file` selector, the file written under `folder`."""
    name = f"{nid}.json"
    with open(os.path.join(folder, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(tools["period"].periods_text(n, rows))
    selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": folder, "pattern": name})
    doc.connect(selector.id, nid, "periods")
    doc.node(nid).params.update(tools["period"].PATHS["periods"](D.pick_path(doc, tools, nid, "periods")[0]))


def walked(app, g):
    """Every cut in time the clip lane walks of `g`: [(start, result)] in the order walked, and the rows each node was stepped over."""
    ready, stepped = [], {}
    g.on_event = lambda ev: ev.kind == "step" and ev.lane == "clip" and stepped.setdefault(ev.node, []).append(ev.row)
    g.halt = False          # a worker stopped halts its graph, and this one walks it again
    w = Worker(g, every=1 << 30)
    w.periodReady.connect(lambda r, s, f: ready.append((s, r)), Qt.DirectConnection)
    w.walk_clip()
    want = sum(len(t.cuts) for t in g.snapshot().timed)
    t0 = time.perf_counter()
    w.start()
    while len(ready) < want and time.perf_counter() - t0 < 20:
        app.processEvents()
        time.sleep(0.01)
    w.stop()
    g.on_event = None
    return ready, stepped


def runs_kept(gate, first):
    g = np.concatenate([[False], np.asarray(gate, bool), [False]])
    edges = np.flatnonzero(g[1:] != g[:-1])
    return [(int(a) + first, int(b) + first) for a, b in zip(edges[::2], edges[1::2])]


if __name__ == "__main__":
    decmod.QUIET = True
    app = QApplication([])
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    region = {**defaults(tools["region"]), **tools["region"].load_geometry(GEOMETRY), "choice": "diamond", "serve clip": False}
    n = Graph(D.load(DOC, tools), Decoder(D.load(DOC, tools).video), tools).count

    folder = tempfile.mkdtemp()
    extents = {}
    for order in (("region", "period"), ("period", "region")):
        doc = D.load(DOC, tools)
        params = {"region": region, "period": defaults(tools["period"])}
        up = "video"
        for name in order:
            up_id = doc.add_node(name, (0.0, 0.0), params[name]).id
            doc.connect(up, up_id)
            if name == "period":
                filed(doc, tools, up_id, PERIODS, n, folder)
            up = up_id
        thr = doc.add_node("threshold", (0.0, 0.0), dict(doc.node("threshold").params)).id
        blobs = doc.add_node("blobs", (0.0, 0.0), dict(doc.node("blobs").params)).id
        doc.connect(up, thr)
        doc.connect(thr, blobs)
        doc.disconnect("track", "in")
        doc.connect(blobs, "track")
        g = Graph(doc, Decoder(doc.video), tools)
        e = g.snapshot().entries["track"]
        extents[order] = [c.extent for c in e.cuts]
        ready, stepped = walked(app, g)
        g.close()
        print(f"{' under '.join(reversed(order))}: track's cuts {[(x.rows, x.rect) for x in extents[order]]}; "
              f"{len(ready)} periods walked, track over {[(s, len(r['track']['signal'])) for s, r in ready]}, "
              f"stepped over each period's rows alone: {stepped.get('track') == [r for a, b in PERIODS for r in range(a, b)]}")
    print(f"the two orders have one extent: {extents[('region', 'period')] == extents[('period', 'region')]}")

    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    blobs = np.empty(n, object)
    blobs[:] = [g.compute("blobs", r) for r in range(n)]
    g.close()
    count = tools["count"]
    whole = count.run(Series(blobs, "k", 0, g.fps), computed(count, defaults(count)))
    band = (float(np.median(whole["signal"])), float(np.max(whole["signal"])))

    upper = doc.add_node("period", (0.0, 0.0), defaults(tools["period"])).id
    filed(doc, tools, upper, UPPER, n, folder)
    blobs_u = doc.add_node("blobs", (0.0, 0.0), dict(doc.node("blobs").params)).id
    gate = doc.add_node("count", (0.0, 0.0), dict(doc.node("count").params)).id
    lower = doc.add_node("period", (0.0, 0.0), defaults(tools["period"])).id
    blobs_l = doc.add_node("blobs", (0.0, 0.0), dict(doc.node("blobs").params)).id
    doc.connect("threshold", upper)
    doc.connect(upper, blobs_u)
    doc.connect(blobs_u, gate)
    doc.node(gate).band = band
    doc.connect(upper, lower)
    doc.connect(gate, lower, "gate")
    doc.connect(lower, blobs_l)
    doc.disconnect("track", "in")
    doc.connect(blobs_l, "track")

    held = {}
    g = Graph(doc, Decoder(doc.video), tools, cut_result=lambda nid, key, within: held.get(within.extent.rows))
    p = g.snapshot()
    print(f"\na period under a period, nothing held: {lower}'s standing {p.entries[lower].standing!r}; "
          f"walked: {[w.chain for w in p.timed]}")
    ready, _ = walked(app, g)
    held.update({(s, s + len(r[gate]["signal"])): r[gate] for s, r in ready})
    print(f"{gate} walked over {sorted(held)}, each holding a gate: {all('gate' in r for r in held.values())}")
    g.sync()
    p = g.snapshot()
    ups, lows = p.entries[upper].cuts, p.entries[lower].cuts
    expected = [x for c in ups for x in runs_kept(held[c.extent.rows]["gate"], c.extent.rows[0])]
    print(f"{lower}: {len(lows)} periods against {len(expected)} runs {gate}'s gate keeps inside the upper periods: "
          f"{'the same' if [c.extent.rows for c in lows] == expected else 'DIFFER'}")
    inside = all(any(made_from(c, u) and u.extent.rows[0] <= c.extent.rows[0] < c.extent.rows[1] <= u.extent.rows[1] for u in ups) for c in lows)
    print(f"each a cut of the upper period it lies in, and inside it: {inside}; none across two: "
          f"{all(sum(made_from(c, u) for u in ups) == 1 for c in lows)}")
    ready, stepped = walked(app, g)
    g.close()
    below = [s for s, r in ready if "track" in r]
    print(f"walked: {[w.chain for w in p.timed]}; track over {len(below)} periods, "
          f"stepped over the lower periods' rows alone: {stepped.get('track') == [r for c in lows for r in range(*c.extent.rows)]}")
    print("first five lower periods:", [c.extent.rows for c in lows[:5]])
