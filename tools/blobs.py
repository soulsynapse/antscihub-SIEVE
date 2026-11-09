"""Frame tool: the 8-connected regions of a mask's nonzero pixels, one record each; mask or gray in, blobs out.

`min_area` and `max_area` (0: none) bound the records kept, in pixels. `angle`, `major`, `minor`
are the moment ellipse as regionprops defines it, angle in degrees from the x axis; `contour` the
outer boundary as (N, 2) x, y, an object column, so the table is not a flat array. With a plane on
the `diff` input, `mean`, `peak` and `core` (pixels at or over `core_threshold`) are read from it;
without it they are NaN, NaN, -1. `split` cuts a region over `max_area` at rising levels of the
diff until it falls into two or more pieces within bounds, and drops it if none does.

The table's dtype, the plane on it and how a column is added are tools/_table.py's.
"""
import cv2
import numpy as np

from tools._draw import draw as draw_table
from tools._table import DTYPE, OUTLINES, moments, plane_dtype

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "blobs", "frame", ("mask", "gray"), "blobs"
INPUTS = {"diff": "gray"}
OPTIONAL = ("diff",)
DEFAULTS = {"min_area": 50, "max_area": 0, "core_threshold": 0, "split": False, "outline": "box"}
MAX_AREA = 100000
SPLIT_STEP = 4            # levels between thresholds tried when splitting
SPLIT_KEEP = 0.2          # a split whose pieces hold less of the region than this is not one


def _records(labels, ids, stats, diff, core_threshold, offset=(0, 0), dtype=DTYPE):
    """One record per label in `ids`, each computed inside its own box from `stats`, so the plane
    is read by the labeling alone; `offset` is added to every coordinate."""
    out = np.empty(len(ids), dtype)
    for k, i in enumerate(ids):
        x, y, w, h, area = (int(v) for v in stats[i])
        win = (slice(y, y + h), slice(x, x + w))
        sub = labels[win] == i
        cx, cy, angle, major, minor = moments(sub)
        contours, _ = cv2.findContours(sub.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        r = out[k]
        r["x"], r["y"], r["w"], r["h"], r["area"] = x + offset[0], y + offset[1], w, h, area
        r["cx"], r["cy"] = x + offset[0] + cx, y + offset[1] + cy
        r["angle"], r["major"], r["minor"] = angle, major, minor
        r["contour"] = max(contours, key=len)[:, 0, :] + np.array((x + offset[0], y + offset[1]), np.int32)
        if diff is None:
            r["mean"], r["peak"], r["core"] = np.nan, np.nan, -1
        else:
            d = diff[win][sub].astype(np.float64)
            r["mean"], r["peak"], r["core"] = d.sum() / area, d.max(), int(np.count_nonzero(d >= core_threshold))
    return out


def _split(crop, lo, hi, core_threshold, offset, dtype):
    whole = int(np.count_nonzero(crop))
    for t in range(int(crop[crop > 0].min()) + 1, int(crop.max()) + 1, SPLIT_STEP):
        fg = (crop >= t).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
        if n <= 2:
            continue
        areas = stats[1:, cv2.CC_STAT_AREA]
        if areas.sum() < SPLIT_KEEP * whole:
            return None
        keep = np.flatnonzero((areas >= lo) & (areas <= hi)) + 1
        if len(keep) >= 2:
            return _records(labels, keep, stats, crop, core_threshold, offset, dtype)
    return None


def find(mask, min_area, max_area=0, diff=None, core_threshold=0, split=False):
    fg = (np.asarray(mask) != 0).astype(np.uint8)
    dtype = plane_dtype(fg.shape)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    area = stats[1:, cv2.CC_STAT_AREA]
    kept = area >= min_area
    if max_area <= 0:
        return _records(labels, np.flatnonzero(kept) + 1, stats, diff, core_threshold, dtype=dtype)
    big = kept & (area > max_area)
    out = _records(labels, np.flatnonzero(kept & ~big) + 1, stats, diff, core_threshold, dtype=dtype)
    pieces = []
    if split and diff is not None:
        for i in np.flatnonzero(big) + 1:
            x, y, w, h, _ = (int(v) for v in stats[i])
            win = (slice(y, y + h), slice(x, x + w))
            crop = np.where(labels[win] == i, diff[win], 0)
            recs = _split(crop, min_area, max_area, core_threshold, (x, y), dtype)
            if recs is not None:
                pieces.append(recs)
    return np.concatenate([out, *pieces]) if pieces else out


def run(frames, row, params):
    return find(frames(row), int(params["min_area"]), int(params["max_area"]), frames(row, "diff"),
                int(params["core_threshold"]), bool(params["split"]))


def draw(painter, row, result, start, params):
    draw_table(painter, result, params.get("outline", "box"))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("min_area", 0, MAX_AREA, DEFAULTS["min_area"])
    w.add_int("max_area", 0, MAX_AREA, DEFAULTS["max_area"])
    w.add_int("core_threshold", 0, 255, DEFAULTS["core_threshold"])
    w.add_bool("split", DEFAULTS["split"])
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, threshold

    sys.exit(play([gray, threshold, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
