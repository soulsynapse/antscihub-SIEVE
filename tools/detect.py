"""Frame tool: the 8-connected regions of a mask, one flat record each, labelled inside the box that holds them all; mask or gray in, blobs out.

blobs' position columns and moment ellipse and none of its others: no `contour`, `mean`, `peak` or
`core`, so the table is a flat array and a reader of a footprint gets the box. `dark` takes the zero
pixels as the regions, a thresholded plate of dark animals on a light floor as it stands; otherwise
the nonzero ones, as blobs. `min_area` and `max_area` (0: none) bound the records kept, in pixels.
The cost is the box around every set pixel, not the plane: one animal on a clean floor is labelled
in a few hundred pixels, and speckle in opposite corners costs the plane.

The plane on the table and how a record meets one are tools/_table.py's.
"""
import cv2
import numpy as np

from tools._draw import draw as draw_table
from tools._table import DTYPE as BLOBS, plane_dtype

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "detect", "frame", ("mask", "gray"), "blobs"
DEFAULTS = {"dark": False, "min_area": 20, "max_area": 0}
MAX_AREA = 100000
DTYPE = np.dtype([(n, BLOBS[n]) for n in ("x", "y", "w", "h", "area", "cx", "cy", "angle", "major", "minor")])


def find(mask, min_area, max_area=0, dark=False):
    """The table of `mask`'s regions, ascending by label, with the plane's shape on its dtype. A
    plane that is not uint8 is read by what is nonzero."""
    fg = np.asarray(mask)
    dtype = plane_dtype(fg.shape, DTYPE)
    if fg.dtype != np.uint8:
        fg = (fg != 0).astype(np.uint8)
    if dark:
        fg = cv2.threshold(fg, 0, 255, cv2.THRESH_BINARY_INV)[1]
    bx, by, bw, bh = cv2.boundingRect(fg)
    if bw == 0:
        return np.empty(0, dtype)
    bw, bh, bx, by = bw + (bx & 1), bh + (by & 1), bx & ~1, by & ~1    # OpenCV numbers by blocks of two: an even corner keeps the plane's order
    _, labels, stats, centre = cv2.connectedComponentsWithStats(fg[by:by + bh, bx:bx + bw], connectivity=8)
    area = stats[:, cv2.CC_STAT_AREA]
    keep = area >= max(min_area, 1)
    if max_area > 0:
        keep &= area <= max_area
    keep[0] = False
    ids = np.flatnonzero(keep)
    out = np.empty(len(ids), dtype)
    if not len(ids):
        return out
    out["x"], out["y"] = stats[ids, cv2.CC_STAT_LEFT] + bx, stats[ids, cv2.CC_STAT_TOP] + by
    out["w"], out["h"], out["area"] = stats[ids, cv2.CC_STAT_WIDTH], stats[ids, cv2.CC_STAT_HEIGHT], area[ids]
    out["cx"], out["cy"] = centre[ids, 0] + bx, centre[ids, 1] + by
    mu = np.empty((len(ids), 3))
    for k, i in enumerate(ids):
        x, y, w, h = stats[i, :4].tolist()
        m = cv2.moments((labels[y:y + h, x:x + w] == i).view(np.uint8), True)
        mu[k] = m["mu20"], m["mu02"], m["mu11"]
    mu /= area[ids, None]
    half, spread = (mu[:, 0] + mu[:, 1]) / 2, np.sqrt(4 * mu[:, 2] ** 2 + (mu[:, 0] - mu[:, 1]) ** 2) / 2
    out["angle"] = np.degrees(0.5 * np.arctan2(2 * mu[:, 2], mu[:, 0] - mu[:, 1]))
    out["major"], out["minor"] = 4 * np.sqrt(np.maximum(half + spread, 0)), 4 * np.sqrt(np.maximum(half - spread, 0))
    return out


def run(frames, row, params):
    return find(frames(row), int(params["min_area"]), int(params["max_area"]), bool(params["dark"]))


def draw(painter, row, result, start, params):
    draw_table(painter, result)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_bool("dark", DEFAULTS["dark"])
    w.add_int("min_area", 0, MAX_AREA, DEFAULTS["min_area"])
    w.add_int("max_area", 0, MAX_AREA, DEFAULTS["max_area"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, threshold

    sys.exit(play([gray, threshold, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
