"""Experiment behind docs/findings/2026-11-13-detect-on-a-thresholded-crop.md: what tools/detect.py costs
a row on a crop2 clip under the threshold that already isolates its animal, beside blobs and beside the
labeling the TRex 1.1.9 port does, and what a bare walk of video, threshold and detect reads a second.

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-13-detect-on-a-thresholded-crop.py [word ...] [clip]

`stages` times each step alone on ROWS held rows, one OpenCV thread, least of three: the Decoder's luma
read, the threshold, detect.find, blobs.find on the inverted mask, connectedComponentsWithStats over the
plane, and the port's label and crop. `same` holds detect's records to blobs' in the columns both have.
`walk` is Graph.walk_row over WALK_ROWS rows with nothing attached, the memo and the decoder cache at
HOLD each: detect with `dark`, then threshold inverted into blobs. `pool` runs threshold and each
labeling over the held rows through a thread pool of 1, 2, 4 and 8. Every word is row-limited to stay
under a minute; the clip defaults to CLIP.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from tools import blobs, detect, threshold  # noqa: E402

CLIP = os.path.join(ROOT, "video-tests", "Thermal hysteresis 4 days",
                    "Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps-crops", "square-1.mp4")
ROWS, WALK_ROWS, START, HOLD = 6000, 20000, 0, 16 << 20
THRESH, MIN_AREA = 163, 20          # the cut of the folder's own document


def port_label(m):
    """The port's frame_record without the packing: label the plane, then cut each kept box into runs."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8, ltype=cv2.CV_16U)
    out = []
    for i in np.flatnonzero(stats[1:, cv2.CC_STAT_AREA] >= MIN_AREA) + 1:
        x, y, w, h = stats[i, :4].tolist()
        inside = np.zeros((h, w + 2), np.bool_)
        inside[:, 1:-1] = labels[y:y + h, x:x + w] == i
        flat = inside.ravel()
        out.append(np.flatnonzero(flat[1:] != flat[:-1]))
    return out


def per_row(fn, items, repeat=3):
    best = 1e9
    for _ in range(repeat):
        t = time.perf_counter()
        for it in items:
            fn(it)
        best = min(best, time.perf_counter() - t)
    return best / len(items) * 1000


def held(clip):
    d = Decoder(clip, cache_bytes=1 << 20)
    d.output = "luma"
    t = time.perf_counter()
    luma = [d.read(START + r).copy() for r in range(ROWS)]
    ms = (time.perf_counter() - t) / ROWS * 1000
    d.close()
    return luma, ms


def cut(f, inv=False):
    return cv2.threshold(f, THRESH, 255, cv2.THRESH_BINARY_INV if inv else cv2.THRESH_BINARY)[1]


def stages(clip):
    luma, t_dec = held(clip)
    light, dark = [cut(f) for f in luma], [cut(f, True) for f in luma]
    tables = [detect.find(m, MIN_AREA, dark=True) for m in light]
    area = np.concatenate([t["area"] for t in tables])
    box = [cv2.boundingRect(m)[2:] for m in dark]
    print(f"\n== stages, ms a row over {ROWS} rows of {luma[0].shape}, least of three, one OpenCV thread; threshold {THRESH}, min_area {MIN_AREA}")
    print(f"   the Decoder's luma read {t_dec:.3f}; threshold {per_row(cut, luma):.4f}")
    print(f"   detect.find, dark {per_row(lambda m: detect.find(m, MIN_AREA, dark=True), light):.4f}; "
          f"on the inverted mask {per_row(lambda m: detect.find(m, MIN_AREA), dark):.4f}")
    print(f"   blobs.find on the inverted mask {per_row(lambda m: blobs.find(m, MIN_AREA), dark):.4f}; "
          f"connectedComponentsWithStats over the plane {per_row(lambda m: cv2.connectedComponentsWithStats(m, connectivity=8), dark):.4f}; "
          f"the port's label and crop {per_row(port_label, dark):.4f}")
    print(f"   records a row {np.mean([len(t) for t in tables]):.3f}, rows with none {sum(len(t) == 0 for t in tables)}, with two or more "
          f"{sum(len(t) > 1 for t in tables)}; area median {np.median(area):.0f}, 5th to 95th {np.percentile(area, 5):.0f} to {np.percentile(area, 95):.0f}")
    print(f"   the box round every dark pixel: median {np.median([w * h for w, h in box]):.0f} px of {luma[0].size}, "
          f"over a tenth of the plane on {sum(w * h > luma[0].size / 10 for w, h in box)} rows")


def same(clip):
    luma, _ = held(clip)
    bad = 0
    for f in luma:
        a, b = detect.find(cut(f), 1, dark=True), blobs.find(cut(f, True), 1)
        ok = len(a) == len(b) and all(np.array_equal(a[k], b[k]) for k in ("x", "y", "w", "h", "area"))
        ok = ok and all(np.allclose(a[k], b[k], atol=1e-3) for k in ("cx", "cy", "major", "minor"))
        ok = ok and np.allclose(np.where(a["major"] - a["minor"] > 1e-3, (a["angle"] - b["angle"] + 90) % 180 - 90, 0), 0, atol=1e-2)
        bad += not ok
    print(f"\n== same: detect's records against blobs' over {ROWS} rows at min_area 1, every column detect has: {bad} rows differ")


def graph(clip, tools, params):
    decmod.QUIET = True
    doc = D.from_tools(tools, clip)
    doc.node("video").params["output"] = "luma"
    doc.connect("video", "threshold")       # from_tools wired nothing to a video still handing out bgr
    for nid, p in params.items():
        doc.node(nid).params.update(p)
    doc.display = tools[-1].NAME
    g = Graph(doc, Decoder(clip, cache_bytes=HOLD), tools, memo_bytes=HOLD)
    g.sync()
    return g


def walk(clip):
    print(f"\n== Graph.walk_row over {WALK_ROWS} rows from {START}, nothing attached, memo and decoder cache {HOLD >> 20} MB each")
    cases = (("video, threshold, detect with dark", [threshold, detect], {"threshold": {"thresh": THRESH}, "detect": {"dark": True, "min_area": MIN_AREA}}),
             ("video, threshold inverted, blobs", [threshold, blobs], {"threshold": {"thresh": THRESH, "invert": True}, "blobs": {"min_area": MIN_AREA}}))
    for label, tools, params in cases:
        for _ in range(2):
            g = graph(clip, tools, params)
            g.walk_row(START)
            t = time.perf_counter()
            n = sum(len(g.walk_row(START + r)) for r in range(1, WALK_ROWS))
            wall = time.perf_counter() - t
            print(f"   {label}: {wall / (WALK_ROWS - 1) * 1000:.3f} ms a row, {(WALK_ROWS - 1) / wall:.0f} rows a second, {n} records")
            g.close()
            g.decoder.close()


def pool(clip):
    luma, _ = held(clip)
    jobs = (("detect.find", lambda f: detect.find(cut(f), MIN_AREA, dark=True)),
            ("blobs.find", lambda f: blobs.find(cut(f, True), MIN_AREA)),
            ("the port's label and crop", lambda f: port_label(cut(f, True))))
    print(f"\n== threshold and a labeling over {ROWS} held rows through a thread pool, rows a second at 1, 2, 4, 8")
    for label, fn in jobs:
        rates = []
        for k in (1, 2, 4, 8):
            with ThreadPoolExecutor(k) as ex:
                t = time.perf_counter()
                list(ex.map(fn, luma, chunksize=32))
                rates.append(ROWS / (time.perf_counter() - t))
        print(f"   {label}: " + ", ".join(f"{r:.0f}" for r in rates))


if __name__ == "__main__":
    cv2.setNumThreads(1)
    words = [a for a in sys.argv[1:] if not a.lower().endswith(".mp4")] or ["stages", "same", "walk", "pool"]
    clip = next((a for a in sys.argv[1:] if a.lower().endswith(".mp4")), CLIP)
    for w in words:
        {"stages": stages, "same": same, "walk": walk, "pool": pool}[w](clip)
