"""Drives a registered tool over a synthetic clip and over windows inside it, as
docs/findings/experiments/window_against_full.py and tests/test_window_against_full.py both do:
each tool on the shortest chain that feeds it, each walk a walk._Walk whose turns are taken on the
caller's thread on a Graph of its own, rows compared by tests/stepping.same. `against_full` is the
seam; the rest is what it is built of. The caller keeps the store and the decoder's read-ahead
off the user's, as tests/conftest.py does.
"""
import os
from contextlib import nullcontext
from types import SimpleNamespace

import numpy as np

from sieve_player import document as D
from sieve_player.bare import _Told
from sieve_player.decoder import EndOfStream
from sieve_player.graph import Graph
from sieve_player.registry import computed, defaults, is_selector, kind, paths, reach_of
from sieve_player.walk import Leg, _Walk, window_legs
from tests.stepping import same

COUNT, H, W = 60, 48, 64
WINDOWS = ((20, 40), (0, 20))      # one in the middle, one touching the clip's start
PRE = {"bgr": [], "hsv": ["hsv"], "gray": ["gray"], "flow": ["gray", "flow"], "signal": ["gray", "reduce"],
       "mask": ["gray", "threshold"], "blobs": ["gray", "threshold", "detect"], "tracks": ["gray", "threshold", "detect", "track"]}
EXTRA = {"attach": ("marks", ["gray", "threshold", "detect"]), "bg-subtract": ("bg", ["background"]), "decode": ("plane", ["gray"]),
         "mask": ("mask", ["gray", "threshold"]), "sample": ("plane", ["gray"]), "combine": ("with", ["gray", "threshold"])}
CHAIN = {"period": ["gray", "period", "reduce", "smooth"]}     # a cut in time shows only in what is walked below it
PARAMS = {"transitions": {"column": "x"}, "resolve": {"columns": "h"},      # a column the synthetic tables have
          "region": {"plate": [H, W], "shapes": [{"name": "box", "polygon": [[4, 4], [60, 4], [60, 44], [4, 44]]}], "choice": "box", "serve clip": False}}
FILES = {"period": ("periods", "periods.json", '{"rows": %d, "periods": [{"name": "p", "first": 10, "end": 50}]}' % COUNT)}


class Footage:
    path = footage_print = "synthetic"
    fps, count, output, scale = 30.0, COUNT, "bgr", 1.0
    decodes = seeks = reads = cache_hits = cache_bytes = cache_limit = 0
    step_ms = seek_ms = None
    scrub = staticmethod(nullcontext)

    def cached(self, row):
        return None

    def read(self, row):
        if not 0 <= row < self.count:
            raise EndOfStream(row)
        f = np.random.default_rng(row).integers(10, 40, (H, W, 3), dtype=np.uint8)
        for k, (y, x, vy, vx) in enumerate(((5, 5, 1, 2), (30, 40, -1, 1), (20, 10, 0, -1))):
            yy, xx = (y + vy * row) % (H - 8), (x + vx * row) % (W - 8)
            f[yy:yy + 6 + k, xx:xx + 6] = 200 + 15 * k
        return f


PROBE = SimpleNamespace(SIEVE_TOOL=True, NAME="probe", KIND="series", EXPECTS=tuple(PRE), PRODUCES="signal", PARAMS={},
                        run=lambda series, params: {"signal": np.zeros(len(series.data), np.float32)})


def chain_doc(name, tools, folder):
    """The document of the shortest chain to `name`, a frame tool closed by the probe, and its node
    id; a path input's file is written under `folder`."""
    t = tools[name]
    pre = CHAIN.get(name) or min((PRE[e] for e in np.atleast_1d(t.EXPECTS) if e in PRE), key=len) + [name]
    doc = D.from_tools([tools[n] for n in pre] + ([PROBE] if kind(t) == "frame" and name not in CHAIN else []))
    nid = next(n.id for n in doc.nodes if n.tool == name)
    doc.node(nid).params.update(PARAMS.get(name, {}))
    if name in EXTRA:
        inp, path = EXTRA[name]
        src = D.VIDEO_TOOL
        for n in path:
            have = next((x.id for x in doc.nodes if x.tool == n and x.id != nid), None)
            if have is None:
                have = doc.add_node(n, (300, 0), defaults(tools[n])).id
                doc.connect(src, have)
            src = have
        doc.connect(src, nid, inp)
    if name in FILES:
        inp, fn, text = FILES[name]
        with open(os.path.join(folder, fn), "w", encoding="utf-8") as f:
            f.write(text)
        doc.node(nid).params.update(paths(t)[inp](os.path.join(folder, fn)))     # the window's _pick_paths does this; the Graph does not
        doc.connect(doc.add_node("file", (300, 0), {**defaults(tools["file"]), "folder": folder, "pattern": fn}).id, nid, inp)
    return doc, nid


def jobs(p, a, b):
    """(plan, cut, walked node, first, end) of each walk that covers a..b: the plan's own range, and
    each leg of a cut in time, the whole cut for the clip and window_legs for a window."""
    legs = [Leg(p.entries[w.heads[0]].src, c, *c.extent.rows) for w in p.timed for c in w.cuts] if (a, b) == (0, COUNT) else window_legs(p, a, b - a)
    return ([(p, None, None, a, b)] if p.chain else []) + [
        (p.of(next(w for w in p.timed if p.entries[w.heads[0]].src == g.walked and g.cut in w.cuts)), g.cut, g.walked, g.first, g.end) for g in legs]


def walked(doc, tools, a, b):
    """{node: (first row, {field: its rows from there}, (first, end) of the rows it is of)}: each
    chain node's per-row fields and each walked node's stack."""
    g = Graph(doc, Footage(), tools)
    g.sync()
    p, out = g.snapshot(), {}
    try:
        for sub, cut, nid, first, end in jobs(p, a, b):
            ready, refused = _Told(), _Told()
            w = _Walk(g, name="window", every=1 << 62, progress=_Told(), ready=ready, refused=refused, failed=_Told(), plan=sub, cut=cut, walked=nid)
            w.begin(first, end - first)
            while w.i < w.length:
                w.turn()
            if refused.last:
                raise RuntimeError(f"refused: {refused.last[0]}")
            ends = (0, COUNT) if cut is None else cut.extent.rows
            if sub.walk in w.stacks:
                out[sub.walk] = (first, {"frame": w.stacks[sub.walk][: w.i]}, ends)
            for n, res in (ready.last[0] if ready.last else {}).items():
                if isinstance(res, dict):
                    out[n] = (first, {f: v for f, v in res.items() if isinstance(v, np.ndarray) and len(v) == end - first}, ends)
    finally:
        g.close()
    return out, p


def summed(p, nid):
    """(before, after) through everything above `nid`, each node's own added along a path and the
    largest path taken, None absorbing."""
    e = p.entries[nid]
    own = (0, 0) if e.tool is None or nid == D.VIDEO_TOOL else reach_of(e.tool, e.computed)
    ups = [summed(p, s) for s in e.srcs.values() if s is not None]
    return tuple(None if own[i] is None or any(u[i] is None for u in ups) else own[i] + max([u[i] for u in ups] or [0]) for i in (0, 1))


def may_differ(r, a, b, reach, ends):
    """Whether row `r` of the window a..b reads past it by `reach`, cut off at `ends`, the clip's or the cut's."""
    before, after = reach
    lo = ends[0] if before is None else max(ends[0], r - before)
    hi = ends[1] - 1 if after is None else min(ends[1] - 1, r + after)
    return lo < a or hi > b - 1


def offsets(rows, a, b):
    return ",".join(f"+{r - a}" if r - a <= b - 1 - r else f"-{b - 1 - r}" for r in rows) or "none"


def against_full(name, tools, folder):
    """(the tool's declared reach under the params it is driven with, why it could not be driven or
    None, its node id, and one tuple per window and walked node: (a, b, node, summed reach, the
    plan's reach, the rows that differ from the full walk, those of them past the summed reach,
    sorted, and the (first, end) the node's rows are of)). `tools` holds the probe beside the registry's."""
    t = tools[name]
    said = reach_of(t, computed(t, {**defaults(t), **PARAMS.get(name, {})}))
    if is_selector(t):
        return said, "a selector: picks a path under a folder and hands out no rows", None, []
    try:
        doc, nid = chain_doc(name, tools, folder)
        full, p = walked(doc, tools, 0, COUNT)
    except Exception as exc:
        return said, f"{type(exc).__name__}: {exc}", None, []
    if nid not in full and not p.timed:
        return said, f"the full walk hands out nothing for it: {p.entries[nid].standing or 'no rows'}", None, []
    out = []
    for a, b in WINDOWS:
        win, _ = walked(doc, tools, a, b)
        for node in sorted(full, key=lambda n: n != nid):
            reach, (f0, fields, ends), (w0, got, _) = summed(p, node), full[node], win.get(node, (a, {}, None))
            rows = range(max(a, ends[0]), min(b, ends[1]))
            bad = sorted({r for f, whole in fields.items() for r in rows
                          if f not in got or not 0 <= r - w0 < len(got[f]) or not same(got[f][r - w0], whole[r - f0])})
            out.append((a, b, node, reach, p.entries[node].reach, bad, [r for r in bad if not may_differ(r, a, b, reach, ends)], ends))
    return said, None, nid, out
