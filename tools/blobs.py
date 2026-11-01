"""Frame tool: the 8-connected regions of a mask's nonzero pixels, one record each; mask or gray in, blobs out.

`min_area` and `max_area` (0: none) bound the records kept, in pixels. `angle`, `major`, `minor`
are the moment ellipse as regionprops defines it, angle in degrees from the x axis; `contour` the
outer boundary as (N, 2) x, y, an object column, so the table is not a flat array. With a plane on
the `diff` input, `mean`, `peak` and `core` (pixels at or over `core_threshold`) are read from it;
without it they are NaN, NaN, -1. `split` cuts a region over `max_area` at rising levels of the
diff until it falls into two or more pieces within bounds, and drops it if none does.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "blobs", "frame", ("mask", "gray"), "blobs"
INPUTS = {"diff": "gray"}
OPTIONAL = ("diff",)
DEFAULTS = {"min_area": 50, "max_area": 0, "core_threshold": 0, "split": False, "outline": "box"}
MAX_AREA = 100000
DTYPE = np.dtype([("x", np.int32), ("y", np.int32), ("w", np.int32), ("h", np.int32), ("area", np.int32),
                  ("cx", np.float32), ("cy", np.float32), ("angle", np.float32),
                  ("major", np.float32), ("minor", np.float32),
                  ("mean", np.float32), ("peak", np.float32), ("core", np.int32), ("contour", object)])
OUTLINES = ("box", "contour")
SPLIT_STEP = 4            # levels between thresholds tried when splitting
SPLIT_KEEP = 0.2          # a split whose pieces hold less of the region than this is not one


def _records(labels, n, stats, diff, core_threshold, offset=(0, 0)):
    out = np.empty(max(n - 1, 0), DTYPE)
    if n <= 1:
        return out
    s = stats[1:]
    out["x"], out["y"] = s[:, cv2.CC_STAT_LEFT] + offset[0], s[:, cv2.CC_STAT_TOP] + offset[1]
    out["w"], out["h"], out["area"] = s[:, cv2.CC_STAT_WIDTH], s[:, cv2.CC_STAT_HEIGHT], s[:, cv2.CC_STAT_AREA]
    ys, xs = np.nonzero(labels)
    lab = labels[ys, xs]
    xs, ys = xs.astype(np.float64), ys.astype(np.float64)
    area = np.bincount(lab, minlength=n)[1:].astype(np.float64)
    cx = np.bincount(lab, xs, n)[1:] / area
    cy = np.bincount(lab, ys, n)[1:] / area
    mu20 = np.bincount(lab, xs * xs, n)[1:] / area - cx * cx
    mu02 = np.bincount(lab, ys * ys, n)[1:] / area - cy * cy
    mu11 = np.bincount(lab, xs * ys, n)[1:] / area - cx * cy
    half, spread = (mu20 + mu02) / 2, np.sqrt(4 * mu11 * mu11 + (mu20 - mu02) ** 2) / 2
    out["cx"], out["cy"] = cx + offset[0], cy + offset[1]
    out["angle"] = np.degrees(0.5 * np.arctan2(2 * mu11, mu20 - mu02))
    out["major"], out["minor"] = 4 * np.sqrt(np.maximum(half + spread, 0)), 4 * np.sqrt(np.maximum(half - spread, 0))
    contours, _ = cv2.findContours((labels > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        out["contour"][labels[c[0, 0, 1], c[0, 0, 0]] - 1] = c[:, 0, :] + np.array(offset, np.int32)
    if diff is None:
        out["mean"], out["peak"], out["core"] = np.nan, np.nan, -1
    else:
        d = diff[labels.nonzero()].astype(np.float64)
        out["mean"] = np.bincount(lab, d, n)[1:] / area
        peak = np.zeros(n)
        np.maximum.at(peak, lab, d)
        out["peak"] = peak[1:]
        out["core"] = np.bincount(lab[d >= core_threshold], minlength=n)[1:]
    return out


def _split(crop, lo, hi, core_threshold, offset):
    whole = int(np.count_nonzero(crop))
    for t in range(int(crop[crop > 0].min()) + 1, int(crop.max()) + 1, SPLIT_STEP):
        fg = (crop >= t).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
        if n <= 2:
            continue
        areas = stats[1:, cv2.CC_STAT_AREA]
        if areas.sum() < SPLIT_KEEP * whole:
            return None
        keep = (areas >= lo) & (areas <= hi)
        if keep.sum() >= 2:
            recs = _records(labels, n, stats, crop, core_threshold, offset)
            return recs[keep]
    return None


def find(mask, min_area, max_area=0, diff=None, core_threshold=0, split=False):
    fg = (np.asarray(mask) != 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    out = _records(labels, n, stats, diff, core_threshold)
    keep = out["area"] >= min_area
    if max_area <= 0:
        return out[keep]
    big = keep & (out["area"] > max_area)
    pieces = []
    if split and diff is not None:
        for i in np.flatnonzero(big):
            b = out[i]
            win = (slice(b["y"], b["y"] + b["h"]), slice(b["x"], b["x"] + b["w"]))
            crop = np.where(labels[win] == i + 1, diff[win], 0)
            recs = _split(crop, min_area, max_area, core_threshold, (b["x"], b["y"]))
            if recs is not None:
                pieces.append(recs)
    return np.concatenate([out[keep & ~big], *pieces]) if pieces else out[keep & ~big]


def run(frames, row, params):
    return find(frames(row), int(params["min_area"]), int(params["max_area"]), frames(row, "diff"),
                int(params["core_threshold"]), bool(params["split"]))


def outline(painter, b, kind):
    """A record's box or contour in the painter's pen; the contour's points are pixel centres, +0.5."""
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QPolygonF

    if kind == "contour" and b["contour"] is not None:
        painter.drawPolygon(QPolygonF([QPointF(float(x) + 0.5, float(y) + 0.5) for x, y in b["contour"]]))
    else:
        painter.drawRect(QRectF(float(b["x"]), float(b["y"]), float(b["w"]), float(b["h"])))


def draw(painter, row, result, start, params, color=(80, 220, 120)):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPen

    if result is None or len(result) == 0:
        return
    pen = QPen(QColor(*color), 0)      # width 0: one device pixel at any zoom
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    for b in result:
        outline(painter, b, params.get("outline", "box"))


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
