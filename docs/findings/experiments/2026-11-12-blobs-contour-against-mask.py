"""Experiment behind docs/findings/2026-11-12-blobs-contour-against-mask.md: what tools/blobs.py pays for a record's contour, against a scratch blobs that keeps the
region's own binary mask in the column instead, on the masks a document's blobs node is fed.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-blobs-contour-against-mask.py [document [rows]] 2>NUL

The masks of the first `rows` rows are computed once through the document's graph and held, so each
variant is timed on the same input with no decode in it: `trace` is tools/blobs.py as it is, `none` the
same with no contour, `mask` with the region's bool crop in the contour column, `label` the labeling alone.
Then what a reader pays for a record's footprint from each, the bytes a row, and a bare walk of the same
rows with the scratch tool in the graph in place of blobs.
"""
import os
import pickle
import sys
import time
import types

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, nbytes  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from tools import _table, blobs, runs  # noqa: E402

REPEATS = 3


def records(labels, ids, stats, diff, core_threshold, dtype, keep):
    """tools/blobs.py's _records with the contour column by `keep`: "none" leaves it None and "mask"
    puts the region's bool crop there."""
    out = np.empty(len(ids), dtype)
    for k, i in enumerate(ids):
        x, y, w, h, area = (int(v) for v in stats[i])
        win = (slice(y, y + h), slice(x, x + w))
        sub = labels[win] == i
        cx, cy, angle, major, minor = _table.moments(sub)
        r = out[k]
        r["x"], r["y"], r["w"], r["h"], r["area"] = x, y, w, h, area
        r["cx"], r["cy"] = x + cx, y + cy
        r["angle"], r["major"], r["minor"] = angle, major, minor
        r["contour"] = sub if keep == "mask" else None
        if diff is None:
            r["mean"], r["peak"], r["core"] = np.nan, np.nan, -1
        else:
            d = diff[win][sub].astype(np.float64)
            r["mean"], r["peak"], r["core"] = d.sum() / area, d.max(), int(np.count_nonzero(d >= core_threshold))
    return out


def find(mask, min_area, max_area, diff, core_threshold, keep):
    """blobs.find without the split, which no document here turns on."""
    fg = (np.asarray(mask) != 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if keep == "label":
        return n
    area = stats[1:, cv2.CC_STAT_AREA]
    kept = (area >= min_area) & ((area <= max_area) if max_area > 0 else True)
    return records(labels, np.flatnonzero(kept) + 1, stats, diff, core_threshold, _table.plane_dtype(fg.shape), keep)


def footprint(b, shape, scale=(1.0, 1.0), outline="contour"):
    """_table.footprint, reading a 2-D bool in the contour column as the mask it would have filled."""
    c = b["contour"] if "contour" in b.dtype.names else None
    if outline != "contour" or c is None or np.asarray(c).dtype != bool:
        return _table.footprint(b, shape, scale, outline)
    sy, sx = scale
    y, x, h, w = (int(b[k]) for k in ("y", "x", "h", "w"))
    import math
    rows = slice(max(math.ceil(y * sy - 0.5), 0), max(min(math.ceil((y + h) * sy - 0.5), shape[0]), 0))
    cols = slice(max(math.ceil(x * sx - 0.5), 0), max(min(math.ceil((x + w) * sx - 0.5), shape[1]), 0))
    iy = np.clip(np.floor((np.arange(rows.start, rows.stop) + 0.5) / sy).astype(int) - y, 0, h - 1)
    ix = np.clip(np.floor((np.arange(cols.start, cols.stop) + 0.5) / sx).astype(int) - x, 0, w - 1)
    return rows, cols, c[np.ix_(iy, ix)]


def scratch(keep):
    """A tool the graph takes for blobs: its own module's names, run() by `keep`."""
    mod = types.ModuleType("blobs")
    mod.__dict__.update({k: v for k, v in vars(blobs).items() if not k.startswith("__")})
    mod.run = lambda frames, row, params: find(frames(row), int(params["min_area"]), int(params["max_area"]), frames(row, "diff"),
                                               int(params["core_threshold"]), keep)
    return mod


def graph(path, keep=None):
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    if keep == "runs":
        tools["blobs"] = runs
    elif keep:
        tools["blobs"] = scratch(keep)
        for m in tools.values():
            if hasattr(m, "footprint"):
                m.footprint = footprint
    st = store.current()
    doc = D.load(path, tools)
    g = Graph(doc, Decoder(doc.video), tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    g.sync()
    return doc, g


def close(g):
    g.close()
    g.decoder.close()


def timed(fn, items):
    t = time.perf_counter()
    out = [fn(*it) for it in items]
    return (time.perf_counter() - t) * 1000 / len(items), out


def main(path, rows):
    doc, g = graph(path)
    nid = next(n.id for n in doc.nodes if n.tool == "blobs" and g.entry(n.id).fed)
    e, p = g.entry(nid), g.entry(nid).params
    rows = min(rows, g.count)
    fed = [(np.array(g.compute(e.src, r)), None if e.srcs.get("diff") is None else np.array(g.compute(e.srcs["diff"], r)))
           for r in range(rows)]
    close(g)
    args = (int(p["min_area"]), int(p["max_area"]), int(p["core_threshold"]))
    print(f"\n== {os.path.basename(path)}: node {nid} reads {e.src}, {fed[0][0].shape[1]}x{fed[0][0].shape[0]}, {rows} rows, "
          f"min_area {args[0]}, max_area {args[1]}, diff {'wired' if fed[0][1] is not None else 'not wired'}")
    variants = {"trace": lambda m, d: blobs.find(m, args[0], args[1], d, args[2], False),
                "none": lambda m, d: find(m, args[0], args[1], d, args[2], "none"),
                "mask": lambda m, d: find(m, args[0], args[1], d, args[2], "mask"),
                "label": lambda m, d: find(m, args[0], args[1], d, args[2], "label"),
                "runs": lambda m, d: runs.find(m, args[0], args[1], d, args[2], False)}
    tables = {}
    for threads in (1, cv2.getNumberOfCPUs()):
        cv2.setNumThreads(threads)
        ms = {k: [] for k in variants}
        for _ in range(REPEATS):
            for k, fn in variants.items():
                t, out = timed(fn, fed)
                ms[k].append(t)
                tables[k] = out
        print(f"   cv2 threads {threads}: ms a row, the least of {REPEATS} and the most")
        for k in variants:
            print(f"      {k:6} {min(ms[k]):.4f} {max(ms[k]):.4f}")
    cv2.setNumThreads(1)
    n = sum(len(t) for t in tables["trace"])
    comps = sum(tables["label"]) / rows - 1
    same = all(len(a) == len(b) and np.array_equal(a["area"], b["area"]) for a, b in zip(tables["trace"], tables["mask"]))
    print(f"   {n / rows:.2f} records a row of {comps:.1f} components labelled; trace and mask keep the same records: {same}")
    shape = fed[0][0].shape
    recs = {k: [(b, shape) for t in tables[k] for b in t] for k in ("trace", "mask", "runs")}
    if n:
        by_place = lambda k: [(b, shape) for t in tables[k] for b in np.sort(t, order=("y", "x", "area"))]  # noqa: E731
        agree = sum(np.array_equal(footprint(*a)[2], _table.footprint(*b)[2]) for a, b in zip(by_place("mask"), by_place("runs")))
        print(f"   runs keeps {len(recs['runs'])} records; its footprint is the mask variant's for {agree} of {n}")
        for k, fn in (("trace", _table.footprint), ("mask", footprint), ("runs", _table.footprint)):
            ts = [timed(fn, recs[k])[0] for _ in range(REPEATS)]
            print(f"   footprint of a record from {k}: {min(ts) * 1000:.1f} us")
        differ = sum(not np.array_equal(_table.footprint(*a)[2], footprint(*b)[2]) for a, b in zip(recs["trace"], recs["mask"]))
        print(f"   records whose filled contour is not their mask, a hole or a diagonal neck: {differ} of {n}")
    for k in ("trace", "none", "mask", "runs"):
        held = sum(nbytes(t) for t in tables[k]) / rows
        print(f"   {k:6} {held:8.0f} bytes a row as nbytes counts them, {sum(len(pickle.dumps(t)) for t in tables[k]) / rows:8.0f} pickled")
    for keep in (None, "runs", None, "runs"):
        doc, g = graph(path, keep)
        t = time.perf_counter()
        for r in range(rows):
            g.walk_row(r)
        print(f"   bare walk of {g._walk()} over the rows, blobs {'as it is' if keep is None else 'replaced by runs'}: "
              f"{(time.perf_counter() - t) * 1000 / rows:.4f} ms a row")
        close(g)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "video-tests", "bg-subtract-compare.json"),
         int(sys.argv[2]) if len(sys.argv) > 2 else 3000)
