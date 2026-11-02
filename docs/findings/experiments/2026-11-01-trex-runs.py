"""Experiment behind docs/findings/2026-11-01-trex-runs-and-frame-parallel.md: what the TGrabs
pipeline's ideas would buy the blobs path here. Ants clip, luma at 0.5, the finding's settings.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-01-trex-runs.py [video] [start] [rows]

Decodes the rows once, then times each stage single-threaded on the held frames: threshold, the
labeling alone, the current blobs.find, its parts, and a run-based feature pass that computes the
moments from horizontal runs in O(runs) and the intensity sums from row cumsums, checked against
the current records. Then threshold+blobs across a thread pool at 1, 2, 4, 8 threads against the
decode time, with OpenCV's own threads on and off. Last, bytes per row for the mask dense, as runs,
as runs plus the pixels under them, and zlib'd.
"""
import os
import sys
import time
import zlib
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import Decoder  # noqa: E402
from tools import blobs  # noqa: E402

PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "video-tests", "00000.MTS")
START = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
ROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 600
THRESH, MIN_AREA, MAX_AREA, CORE = 79, 230, 17000, 205


def ms(samples):
    a = np.asarray(samples) * 1000
    return f"p50 {np.median(a):6.2f}  p95 {np.percentile(a, 95):6.2f}  mean {a.mean():6.2f} ms"


def timed(fn, frames):
    out, t = [], []
    for f in frames:
        t0 = time.perf_counter()
        out.append(fn(f))
        t.append(time.perf_counter() - t0)
    return out, t


def runs_of(mask):
    """(y, x0, x1) of every horizontal run of nonzero pixels, row-major, inclusive x1."""
    m = mask != 0
    pad = np.zeros((m.shape[0], m.shape[1] + 2), np.int8)
    pad[:, 1:-1] = m
    d = np.diff(pad, axis=1)
    ys, x0 = np.nonzero(d == 1)
    _, x1 = np.nonzero(d == -1)
    return ys, x0, x1 - 1


def sum_sq(a, b):
    """sum of x*x for x in a..b inclusive, as float64."""
    a, b = a.astype(np.float64), b.astype(np.float64)
    return (b * (b + 1) * (2 * b + 1) - (a - 1) * a * (2 * a - 1)) / 6


def records_from_runs(labels, n, stats, diff, core_threshold, mask):
    """The current record's numeric columns, the moments from runs and the intensities from row
    cumsums; contour and peak as blobs._records computes them."""
    out = np.empty(max(n - 1, 0), blobs.DTYPE)
    if n <= 1:
        return out
    s = stats[1:]
    out["x"], out["y"] = s[:, cv2.CC_STAT_LEFT], s[:, cv2.CC_STAT_TOP]
    out["w"], out["h"], out["area"] = s[:, cv2.CC_STAT_WIDTH], s[:, cv2.CC_STAT_HEIGHT], s[:, cv2.CC_STAT_AREA]
    ys, x0, x1 = runs_of(mask)
    lab = labels[ys, x0]
    cnt = (x1 - x0 + 1).astype(np.float64)
    yf = ys.astype(np.float64)
    sx = cnt * (x0 + x1) / 2
    area = np.bincount(lab, cnt, n)[1:]
    cx = np.bincount(lab, sx, n)[1:] / area
    cy = np.bincount(lab, yf * cnt, n)[1:] / area
    mu20 = np.bincount(lab, sum_sq(x0, x1), n)[1:] / area - cx * cx
    mu02 = np.bincount(lab, yf * yf * cnt, n)[1:] / area - cy * cy
    mu11 = np.bincount(lab, yf * sx, n)[1:] / area - cx * cy
    half, spread = (mu20 + mu02) / 2, np.sqrt(4 * mu11 * mu11 + (mu20 - mu02) ** 2) / 2
    out["cx"], out["cy"] = cx, cy
    out["angle"] = np.degrees(0.5 * np.arctan2(2 * mu11, mu20 - mu02))
    out["major"], out["minor"] = 4 * np.sqrt(np.maximum(half + spread, 0)), 4 * np.sqrt(np.maximum(half - spread, 0))
    contours, _ = cv2.findContours((labels > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        out["contour"][labels[c[0, 0, 1], c[0, 0, 0]] - 1] = c[:, 0, :]
    if diff is None:
        out["mean"], out["peak"], out["core"] = np.nan, np.nan, -1
        return out
    cs = np.zeros((diff.shape[0], diff.shape[1] + 1), np.float64)
    np.cumsum(diff, axis=1, dtype=np.float64, out=cs[:, 1:])
    out["mean"] = np.bincount(lab, cs[ys, x1 + 1] - cs[ys, x0], n)[1:] / area
    cc = np.zeros_like(cs, dtype=np.int32)
    np.cumsum(diff >= core_threshold, axis=1, dtype=np.int32, out=cc[:, 1:])
    out["core"] = np.bincount(lab, cc[ys, x1 + 1] - cc[ys, x0], n)[1:]
    d = diff[labels.nonzero()].astype(np.float64)
    peak = np.zeros(n)
    np.maximum.at(peak, labels[labels.nonzero()], d)
    out["peak"] = peak[1:]
    return out


def find_runs(mask, diff):
    fg = (mask != 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    out = records_from_runs(labels, n, stats, diff, CORE, mask)
    keep = (out["area"] >= MIN_AREA) & (out["area"] <= MAX_AREA)
    return out[keep]


def main():
    dec = Decoder(PATH)
    dec.output, dec.scale = "luma", 0.5
    print(f"{PATH}: {dec.width}x{dec.height} @ {dec.fps:.2f} fps; rows {START}..{START + ROWS - 1} at 0.5, luma; "
          f"threshold {THRESH} inverted, blobs {MIN_AREA}..{MAX_AREA}, core {CORE}; cv2 threads {cv2.getNumThreads()}, "
          f"cpus {os.cpu_count()}")

    t0 = time.perf_counter()
    frames = [dec.read(r) for r in range(START, START + ROWS)]
    t_decode = time.perf_counter() - t0
    dec.close()
    print(f"\ndecode {ROWS} rows sequentially: {t_decode:.2f} s, {t_decode / ROWS * 1000:.2f} ms/row "
          f"({frames[0].shape[1]}x{frames[0].shape[0]}, {frames[0].nbytes >> 10} KB a row)")

    def thr(f):
        return cv2.threshold(f, THRESH, 255, cv2.THRESH_BINARY_INV)[1]

    masks, t_thr = timed(thr, frames)
    diffs = [255 - f for f in frames]
    pairs = list(zip(masks, diffs))

    def cc_stats(p):
        return cv2.connectedComponentsWithStats((p[0] != 0).astype(np.uint8), connectivity=8)

    def cc_plain(p):
        return cv2.connectedComponents((p[0] != 0).astype(np.uint8), connectivity=8)

    def cur(p):
        return old_find(p)

    def cur_nodiff(p):
        return old_find((p[0], None))

    def new(p):
        return find_runs(p[0], p[1])

    def new_nodiff(p):
        return find_runs(p[0], None)

    # The finding's figures were taken when blobs.find was the full-plane pass below; find is now
    # crop_first, and these two stay as the paths it was measured against.

    def full_plane(labels, n, stats, diff):
        """The feature pass as it was: every column from bincounts over the whole plane's pixels."""
        out = np.empty(max(n - 1, 0), blobs.DTYPE)
        if n <= 1:
            return out
        s = stats[1:]
        out["x"], out["y"], out["w"], out["h"], out["area"] = s[:, 0], s[:, 1], s[:, 2], s[:, 3], s[:, 4]
        ys, xs = np.nonzero(labels)
        lab = labels[ys, xs]
        xs, ys = xs.astype(np.float64), ys.astype(np.float64)
        area = np.bincount(lab, minlength=n)[1:].astype(np.float64)
        cx, cy = np.bincount(lab, xs, n)[1:] / area, np.bincount(lab, ys, n)[1:] / area
        mu20 = np.bincount(lab, xs * xs, n)[1:] / area - cx * cx
        mu02 = np.bincount(lab, ys * ys, n)[1:] / area - cy * cy
        mu11 = np.bincount(lab, xs * ys, n)[1:] / area - cx * cy
        half, spread = (mu20 + mu02) / 2, np.sqrt(4 * mu11 * mu11 + (mu20 - mu02) ** 2) / 2
        out["cx"], out["cy"] = cx, cy
        out["angle"] = np.degrees(0.5 * np.arctan2(2 * mu11, mu20 - mu02))
        out["major"], out["minor"] = 4 * np.sqrt(np.maximum(half + spread, 0)), 4 * np.sqrt(np.maximum(half - spread, 0))
        contours, _ = cv2.findContours((labels > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            out["contour"][labels[c[0, 0, 1], c[0, 0, 0]] - 1] = c[:, 0, :]
        if diff is None:
            out["mean"], out["peak"], out["core"] = np.nan, np.nan, -1
        else:
            d = diff[labels.nonzero()].astype(np.float64)
            out["mean"] = np.bincount(lab, d, n)[1:] / area
            peak = np.zeros(n)
            np.maximum.at(peak, lab, d)
            out["peak"] = peak[1:]
            out["core"] = np.bincount(lab[d >= CORE], minlength=n)[1:]
        return out

    def old_find(p):
        fg = (p[0] != 0).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
        out = full_plane(labels, n, stats, p[1])
        return out[(out["area"] >= MIN_AREA) & (out["area"] <= MAX_AREA)]

    def filter_first(p):
        """The old pass with the area bounds applied to the stats first: the labels image is
        relabeled to the kept components and the pass runs over those alone, still over the plane."""
        fg = (p[0] != 0).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
        area = stats[1:, cv2.CC_STAT_AREA]
        keep = np.flatnonzero((area >= MIN_AREA) & (area <= MAX_AREA)) + 1
        lut = np.zeros(n, np.int32)
        lut[keep] = np.arange(1, len(keep) + 1)
        return full_plane(lut[labels], len(keep) + 1, stats[np.r_[0, keep]], p[1])

    def crop_first(p):
        return blobs.find(p[0], MIN_AREA, MAX_AREA, p[1], CORE, False)

    def only_runs(p):
        return runs_of(p)

    def only_contours(p):
        return cv2.findContours(p[0], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for threads in (cv2.getNumThreads(), 1):
        cv2.setNumThreads(threads)
        print(f"\n-- single thread per stage, cv2 threads = {cv2.getNumThreads()} --")
        print(f"threshold                         {ms(timed(thr, frames)[1])}")
        ccs, t = timed(cc_stats, pairs)
        print(f"connectedComponentsWithStats      {ms(t)}")
        print(f"connectedComponents (no stats)    {ms(timed(cc_plain, pairs)[1])}")
        print(f"findContours on the mask          {ms(timed(only_contours, masks)[1])}")
        rr, t = timed(only_runs, masks)
        print(f"runs_of (vectorized RLE)          {ms(t)}   runs/row p50 {np.median([len(r[0]) for r in rr]):.0f}")
        a, t_cur = timed(cur, pairs)
        print(f"blobs.find, full plane, with diff {ms(t_cur)}")
        b, t_new = timed(new, pairs)
        print(f"blobs.find via runs, with diff    {ms(t_new)}")
        print(f"blobs.find, full plane, no diff   {ms(timed(cur_nodiff, pairs)[1])}")
        print(f"blobs.find via runs, no diff      {ms(timed(new_nodiff, pairs)[1])}")
        c, t_ff = timed(filter_first, pairs)
        print(f"blobs.find, filter first, w/ diff {ms(t_ff)}")
        e, t_cf = timed(crop_first, pairs)
        print(f"blobs.find, crop first, with diff {ms(t_cf)}")
        print(f"blobs.find, crop first, no diff   {ms(timed(lambda p: crop_first((p[0], None)), pairs)[1])}")
        comps = [len(c[2]) - 1 for c in ccs]
        print(f"components/row p50 {np.median(comps):.0f} p95 {np.percentile(comps, 95):.0f}; "
              f"kept/row p50 {np.median([len(x) for x in a]):.1f}")

    # the per-pixel path's parts, cv2 threads back on
    cv2.setNumThreads(os.cpu_count())
    lab0 = ccs[0][1]
    diff0 = diffs[0]

    def part_gather(_):
        ys, xs = np.nonzero(lab0)
        return lab0[ys, xs], xs.astype(np.float64), ys.astype(np.float64)

    lab, xs, ys = part_gather(None)
    n = len(ccs[0][2])

    def part_moments(_):
        area = np.bincount(lab, minlength=n)[1:].astype(np.float64)
        return (np.bincount(lab, xs, n)[1:] / area, np.bincount(lab, ys, n)[1:] / area,
                np.bincount(lab, xs * xs, n)[1:], np.bincount(lab, ys * ys, n)[1:], np.bincount(lab, xs * ys, n)[1:])

    def part_peak(_):
        d = diff0[lab0.nonzero()].astype(np.float64)
        peak = np.zeros(n)
        np.maximum.at(peak, lab, d)
        return peak

    def part_mean_core(_):
        d = diff0[lab0.nonzero()].astype(np.float64)
        return np.bincount(lab, d, n), np.bincount(lab[d >= CORE], minlength=n)

    reps = [None] * 50
    print("\n-- the current per-pixel pass, row 0, parts --")
    print(f"np.nonzero + gather               {ms(timed(part_gather, reps)[1])}")
    print(f"five bincounts (moments)          {ms(timed(part_moments, reps)[1])}")
    print(f"mean + core bincounts             {ms(timed(part_mean_core, reps)[1])}")
    print(f"peak via np.maximum.at            {ms(timed(part_peak, reps)[1])}")

    # equality of the two record sets
    worst = {k: 0.0 for k in ("area", "cx", "cy", "angle", "major", "minor", "mean", "core")}
    mismatch = 0
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            mismatch += 1
            continue
        for k in worst:
            x, y = ra[k].astype(np.float64), rb[k].astype(np.float64)
            worst[k] = max(worst[k], float(np.max(np.abs(x - y))) if len(x) else 0.0)
    print(f"\nrun-based vs current records: rows with a different count {mismatch}/{ROWS}; "
          "max abs difference per column " + ", ".join(f"{k} {v:.2e}" for k, v in worst.items()))
    same = sum(len(ra) == len(rc) and all(np.array_equal(ra[k], rc[k]) for k in worst) for ra, rc in zip(a, c))
    print(f"filter-first vs current records: identical on {same}/{ROWS} rows")
    cols = tuple(worst) + ("x", "y", "w", "h", "peak")
    same = sum(len(ra) == len(re) and all(np.array_equal(ra[k], re[k]) for k in cols)
               and all(np.array_equal(u, v) for u, v in zip(ra["contour"], re["contour"])) for ra, re in zip(a, e))
    print(f"crop-first vs current records: identical on {same}/{ROWS} rows, contours included")

    def work_crop(p):
        return crop_first((thr(p[0]), p[1]))

    cv2.setNumThreads(1)
    with ThreadPoolExecutor(8) as ex:
        t0 = time.perf_counter()
        list(ex.map(work_crop, list(zip(frames, diffs))))
        dt = time.perf_counter() - t0
    print(f"threshold + crop-first blobs, 8 workers, cv2 threads 1: {dt:.2f} s, {dt / ROWS * 1000:.2f} ms/row; "
          f"serial {sum(t_cf):.2f} s")

    def work(p):
        return blobs.find(thr(p[0]), MIN_AREA, MAX_AREA, p[1], CORE, False)

    fd = list(zip(frames, diffs))
    for threads in (os.cpu_count(), 1):
        cv2.setNumThreads(threads)
        print(f"\n-- threshold+blobs over {ROWS} held rows, thread pool, cv2 threads = {cv2.getNumThreads()} --")
        for n_workers in (1, 2, 4, 8, 16):
            with ThreadPoolExecutor(n_workers) as ex:
                t0 = time.perf_counter()
                res = list(ex.map(work, fd))
                dt = time.perf_counter() - t0
            print(f"{n_workers:2d} workers: {dt:6.2f} s  {dt / ROWS * 1000:6.2f} ms/row  "
                  f"x{(t_cur and sum(t_cur)) / dt:4.2f} vs serial; decode alone was {t_decode:.2f} s")
            assert len(res) == ROWS

    print(f"\n-- decode {ROWS} rows split across N captures, each seeking to its chunk, luma at 0.5 --")
    for n_caps in (1, 2, 4, 8):
        chunks = np.array_split(np.arange(START, START + ROWS), n_caps)

        def chunk(rows):
            d = Decoder(PATH, cache_bytes=0)
            d.output, d.scale = "luma", 0.5
            out = [d.read(int(r)) for r in rows]
            d.close()
            return len(out)

        with ThreadPoolExecutor(n_caps) as ex:
            t0 = time.perf_counter()
            got = sum(ex.map(chunk, chunks))
            dt = time.perf_counter() - t0
        print(f"{n_caps:2d} captures: {dt:6.2f} s  {got / dt:6.0f} rows/s  x{t_decode / dt:4.2f} vs one")

    print("\n-- bytes a row for the mask --")
    dense = masks[0].nbytes
    runs = np.median([len(r[0]) for r in rr])
    px = np.median([int(np.count_nonzero(m)) for m in masks])
    z_dense = np.median([len(zlib.compress(np.packbits(m != 0).tobytes(), 1)) for m in masks[:50]])
    print(f"dense uint8 {dense >> 10} KB; packbits {dense // 8 >> 10} KB; runs x 4 B {runs * 4 / 1024:.1f} KB; "
          f"runs + pixels under them {(runs * 4 + px) / 1024:.1f} KB; packbits+zlib(1) {z_dense / 1024:.1f} KB; "
          f"nonzero px/row p50 {px:.0f}")


if __name__ == "__main__":
    main()
