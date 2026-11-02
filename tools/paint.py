"""Frame tool: a table's records painted into a mask the shape of the plane they were found in;
blobs in, mask out.

`outline` paints each record's contour filled or its box; a record with no contour gets its box
either way, as draw shows it. No records is an empty mask. A table with no plane on it raises.
`footprint` is the per-record mask sample reads a plane through, in that plane's coordinates.
"""
import math

import cv2
import numpy as np

from tools.blobs import plane

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "paint", "frame", "blobs", "mask"
OUTLINES = ("contour", "box")
DEFAULTS = {"outline": "contour"}


def footprint(b, shape, scale=(1.0, 1.0), outline="contour"):
    """Where record `b` lies in a plane of `shape`, as (rows, cols, inside): the slices of the plane
    pixels whose centres fall in its box scaled by `scale` (y, x), and the bool mask within them of
    those whose centres fall in its filled contour, or in the whole box when `outline` is box or
    the record has no contour. A plane pixel is inside by its centre, so a record covers the same
    ground at any scale."""
    sy, sx = scale
    y, x, h, w = (int(b[k]) for k in ("y", "x", "h", "w"))
    rows = slice(max(math.ceil(y * sy - 0.5), 0), max(min(math.ceil((y + h) * sy - 0.5), shape[0]), 0))
    cols = slice(max(math.ceil(x * sx - 0.5), 0), max(min(math.ceil((x + w) * sx - 0.5), shape[1]), 0))
    contour = b["contour"] if outline == "contour" and "contour" in b.dtype.names else None
    if contour is None:
        local = np.ones((h, w), bool)
    else:
        local = np.zeros((h, w), np.uint8)
        cv2.fillPoly(local, [(np.asarray(contour, np.int32) - (x, y)).reshape(-1, 1, 2)], 1)
        local = local.astype(bool)
    iy = np.clip(np.floor((np.arange(rows.start, rows.stop) + 0.5) / sy).astype(int) - y, 0, h - 1)
    ix = np.clip(np.floor((np.arange(cols.start, cols.stop) + 0.5) / sx).astype(int) - x, 0, w - 1)
    return rows, cols, local[np.ix_(iy, ix)]


def paint(table, outline="contour"):
    shape = plane(table)
    if shape is None:
        raise ValueError("the table carries no plane to paint into")
    out = np.zeros(shape, np.uint8)
    for b in table:
        rows, cols, inside = footprint(b, shape, outline=outline)
        out[rows, cols][inside] = 255
    return out


def run(frames, row, params):
    return paint(frames(row), params["outline"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w
