"""The one-off of docs/findings/window-against-full.md: every registered tool on the shortest chain
that feeds it from synthetic footage, walked over the whole clip and over two windows inside it,
each node's rows compared against the whole clip's.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\window_against_full.py

The footage is COUNT rows of bright squares drifting over seeded noise, a row's pixels a function of
its row alone. Each walk is walk._Walk driven by its turns on this thread, as bare.py drives one, on
a Graph of its own; a chain below a cut in time is walked leg by leg as the worker's lanes walk it,
the clip's over each cut whole and the window's over walk.window_legs. A frame tool is read through
a series probe below it, so the walk stacks its rows. Rows are compared by tests/stepping.same:
exact for integers, tables and object rows, NaN equal to NaN for floats, dtype for dtype.
"""
import os
import sys
import tempfile
from contextlib import nullcontext
from types import SimpleNamespace

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402

from sieve_player import decoder as decmod, store  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.bare import _Told  # noqa: E402
from sieve_player.decoder import EndOfStream  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import computed, defaults, discover, is_selector, kind, paths, reach_of  # noqa: E402
from sieve_player.walk import Leg, _Walk, window_legs  # noqa: E402
from tests.stepping import same  # noqa: E402

COUNT, H, W = 60, 48, 64
WINDOWS = ((20, 40), (0, 20))      # one in the middle, one touching the clip's start
PRE = {"bgr": [], "hsv": ["hsv"], "gray": ["gray"], "flow": ["gray", "flow"], "signal": ["gray", "reduce"],
       "mask": ["gray", "threshold"], "blobs": ["gray", "threshold", "detect"], "tracks": ["gray", "threshold", "detect", "track"]}
EXTRA = {"attach": ("marks", ["gray", "threshold", "detect"]), "bg-subtract": ("bg", ["background"]), "decode": ("plane", ["gray"]),
         "mask": ("mask", ["gray", "threshold"]), "sample": ("plane", ["gray"]), "combine": ("with", ["gray", "threshold"])}
CHAIN = {"period": ["gray", "period", "reduce", "smooth"]}     # a cut in time shows only in what is walked below it
PARAMS = {"transitions": {"column": "x"}, "resolve": {"columns": "h"},      # a column the synthetic tables have
          "region": {"plate": [H, W], "shapes": [{"name": "box", "polygon": [[4, 4], [60, 4], [60, 44], [4, 44]]}], "choice": "box", "serve clip": False}}
TMP = tempfile.mkdtemp(prefix="window-against-full-")
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


def chain_doc(name, tools):
    """The document of the shortest chain to `name`, a frame tool closed by the probe, and its node id."""
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
        with open(os.path.join(TMP, fn), "w", encoding="utf-8") as f:
            f.write(text)
        doc.node(nid).params.update(paths(t)[inp](os.path.join(TMP, fn)))     # the window's _pick_paths does this; the Graph does not
        doc.connect(doc.add_node("file", (300, 0), {**defaults(tools["file"]), "folder": TMP, "pattern": fn}).id, nid, inp)
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


def main():
    decmod.QUIET = True
    decmod.read_frame_times_ahead = lambda path, then=None: None
    decmod.STORE = None
    store.CHOICE = os.path.join(TMP, "store.txt")
    os.environ[store.STORE_ENV] = os.path.join(TMP, "store")
    tools = {**{e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}, "probe": PROBE}
    counts = {"HOLDS": 0, "BREAKS": 0, "SKIPPED": 0}
    print(f"{COUNT} rows; windows {WINDOWS}; a differing row as +k from the window's first row or -k from its last")
    for name in sorted(set(tools) - {"probe"}):
        t = tools[name]
        said = reach_of(t, computed(t, {**defaults(t), **PARAMS.get(name, {})}))
        why = "a selector: picks a path under a folder and hands out no rows" if is_selector(t) else None
        if why is None:
            try:
                doc, nid = chain_doc(name, tools)
                full, p = walked(doc, tools, 0, COUNT)
                if nid not in full and not p.timed:
                    why = f"the full walk hands out nothing for it: {p.entries[nid].standing or 'no rows'}"
            except Exception as exc:
                why = f"{type(exc).__name__}: {exc}"
        if why is not None:
            counts["SKIPPED"] += 1
            print(f"{name:<14} {str(said):<13} SKIPPED  {why}")
            continue
        verdict, parts = "HOLDS", []
        for a, b in WINDOWS:
            win, _ = walked(doc, tools, a, b)
            for node in sorted(full, key=lambda n: n != nid):
                reach, (f0, fields, ends), (w0, got, _) = summed(p, node), full[node], win.get(node, (a, {}, None))
                if reach != p.entries[node].reach:
                    parts.append(f"{node} summed {reach}, the plan says {p.entries[node].reach}")
                rows = range(max(a, ends[0]), min(b, ends[1]))
                bad = {r for f, whole in fields.items() for r in rows
                       if f not in got or not 0 <= r - w0 < len(got[f]) or not same(got[f][r - w0], whole[r - f0])}
                over = sorted(r for r in bad if not may_differ(r, a, b, reach, ends))
                if node == nid or over or node in CHAIN.get(name, ()):
                    parts.append(f"[{a},{b}) {node} {reach}: {offsets(sorted(bad), a, b)}" + (f" PAST AT {offsets(over, a, b)}" if over else ""))
                verdict = "BREAKS" if over else verdict
        counts[verdict] += 1
        print(f"{name:<14} {str(said):<13} {verdict:<8} " + "; ".join(parts))
    print(" ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
