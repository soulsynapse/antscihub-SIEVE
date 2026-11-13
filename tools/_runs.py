"""The labeling by runs the blob tools over a mask share: a mask's runs joined into 8-connected regions,
and a blobs table of them with each region's runs in its `runs` column. Not a tool; `runs` is the tool
over a mask and `segment` the one over a frame and its background. The table's dtype and how a record
meets a plane are tools/_table.py's.
"""
import numpy as np

from tools._table import RUNS_DTYPE as DTYPE, filled, plane, plane_dtype

SPLIT_STEP = 4            # levels between thresholds tried when splitting
SPLIT_KEEP = 0.2          # a split whose pieces hold less of the region than this is not one


def _label(mask):
    """The runs of `mask`'s nonzero pixels in raster order as (y, x0, x1, region, area): x1 one past
    the run's last pixel, `region` the index of the first run of the 8-connected region the run is
    in, and `area` the pixels of the region each run index heads, 0 where it heads none."""
    fg = np.asarray(mask) != 0
    h, w = fg.shape
    pad = np.zeros((h, w + 2), bool)
    pad[:, 1:-1] = fg
    edge = np.flatnonzero(pad[:, 1:] != pad[:, :-1])
    lo, hi = edge[0::2], edge[1::2]         # a run's first pixel and one past its last, each as y * (w + 1) + x
    n = len(lo)
    first = np.searchsorted(hi, lo - (w + 1), "left")       # the runs of the row above a run touches are first to past
    above = np.searchsorted(lo, hi - (w + 1), "right") - first
    head = np.where(above > 0, first, np.arange(n))
    while not np.array_equal(up := head[head], head):
        head = up
    more = np.flatnonzero(above > 1)        # a run under several joins what each of them heads
    if len(more):
        extra = above[more] - 1
        under = np.repeat(more, extra)
        a = head[first[under] + 1 + np.arange(len(under)) - np.repeat(np.cumsum(extra) - extra, extra)]
        b = head[under]
        pairs = np.unique(np.minimum(a, b)[a != b] * n + np.maximum(a, b)[a != b])
        into = {}

        def root(i):
            while i in into:
                i = into[i]
            return i

        for p in pairs.tolist():
            i, j = root(p // n), root(p % n)
            if i != j:
                into[max(i, j)] = min(i, j)
        if into:
            to = np.arange(n)
            for i in into:
                to[i] = root(i)
            head = to[head]
    y = lo // (w + 1)
    x0, x1 = lo - y * (w + 1), hi - y * (w + 1)
    return y, x0, x1, head, np.bincount(head, x1 - x0, n)


def _records(y, x0, x1, region, keep, dtype, diff, core_threshold, offset=(0, 0)):
    """One record per region in `keep`, ascending; `offset` is added to every coordinate."""
    if not len(keep):
        return np.empty(0, dtype)
    flag = np.zeros(len(y), bool)
    flag[keep] = True
    sel = np.flatnonzero(flag[region])
    sel = sel[np.argsort(region[sel], kind="stable")]
    y, x0, x1, region = y[sel], x0[sel], x1[sel], region[sel]
    cut = np.flatnonzero(np.diff(region, prepend=-1))       # where each region's runs begin
    count = np.diff(cut, append=len(region))
    bx, by = np.minimum.reduceat(x0, cut), y[cut]
    width, height = np.maximum.reduceat(x1, cut) - bx, y[cut + count - 1] - by + 1

    def total(v):
        return np.add.reduceat(v, cut)

    # sums over a run of n pixels from a to b - 1, in the region's own box so a shifted mask gives the same moments
    a, b, r = (x0 - np.repeat(bx, count)).astype(np.float64), (x1 - np.repeat(bx, count)).astype(np.float64), (y - np.repeat(by, count)).astype(np.float64)
    n = b - a
    sx = n * (a + b - 1) / 2
    area = total(n)
    cx, cy = total(sx) / area, total(n * r) / area
    mu20 = total((b - 1) * b * (2 * b - 1) / 6 - (a - 1) * a * (2 * a - 1) / 6) / area - cx * cx
    mu02, mu11 = total(n * r * r) / area - cy * cy, total(r * sx) / area - cx * cy
    half, spread = (mu20 + mu02) / 2, np.sqrt(4 * mu11 * mu11 + (mu20 - mu02) ** 2) / 2

    out = np.empty(len(cut), dtype)
    out["x"], out["y"], out["w"], out["h"], out["area"] = bx + offset[0], by + offset[1], width, height, area
    out["cx"], out["cy"] = bx + offset[0] + cx, by + offset[1] + cy
    out["angle"] = np.degrees(0.5 * np.arctan2(2 * mu11, mu20 - mu02))
    out["major"], out["minor"] = 4 * np.sqrt(np.maximum(half + spread, 0)), 4 * np.sqrt(np.maximum(half - spread, 0))
    if diff is None:
        out["mean"], out["peak"], out["core"] = np.nan, np.nan, -1
    else:
        n = x1 - x0
        begin = np.cumsum(n) - n
        v = np.asarray(diff).reshape(-1)[np.repeat(y * diff.shape[1] + x0 - begin, n) + np.arange(n.sum())]
        out["mean"] = np.add.reduceat(v.astype(np.float64), begin[cut]) / area
        out["peak"] = np.maximum.reduceat(v, begin[cut])
        out["core"] = np.add.reduceat((v >= core_threshold).astype(np.int64), begin[cut])
    kept = np.stack((y + offset[1], x0 + offset[0], x1 + offset[0]), axis=1).astype(np.uint16 if max(plane(out)) < 1 << 16 else np.int32)
    column = out["runs"]
    for k, piece in enumerate(np.split(kept, cut[1:])):
        column[k] = piece
    return out


def _split(crop, lo, hi, core_threshold, offset, dtype):
    whole = int(np.count_nonzero(crop))
    for t in range(int(crop[crop > 0].min()) + 1, int(crop.max()) + 1, SPLIT_STEP):
        y, x0, x1, region, area = _label(crop >= t)
        if np.count_nonzero(area) < 2:
            continue
        if area.sum() < SPLIT_KEEP * whole:
            return None
        keep = np.flatnonzero((area >= max(lo, 1)) & (area <= hi))
        if len(keep) >= 2:
            return _records(y, x0, x1, region, keep, dtype, crop, core_threshold, offset)
    return None


def find(mask, min_area, max_area=0, diff=None, core_threshold=0, split=False):
    dtype = plane_dtype(np.shape(mask), DTYPE)
    y, x0, x1, region, area = _label(mask)
    kept = area >= max(min_area, 1)
    big = kept & (area > max_area) if max_area > 0 else np.zeros(len(y), bool)
    out = _records(y, x0, x1, region, np.flatnonzero(kept & ~big), dtype, diff, core_threshold)
    pieces = []
    if split and diff is not None:
        for i in np.flatnonzero(big):
            of = region == i
            ry, ra, rb = y[of], x0[of], x1[of]
            bx, by = int(ra.min()), int(ry[0])
            inside = filled(ry - by, ra - bx, rb - bx, (int(ry[-1]) - by + 1, int(rb.max()) - bx))
            crop = np.where(inside, diff[by:by + inside.shape[0], bx:bx + inside.shape[1]], 0)
            recs = _split(crop, min_area, max_area, core_threshold, (bx, by), dtype)
            if recs is not None:
                pieces.append(recs)
    return np.concatenate([out, *pieces]) if pieces else out
