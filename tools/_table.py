"""The table kind the blob tools share: its dtype, the plane it was found in, how a column is added,
how a record meets a plane, the moments of a filled region and how a bound knob reads. Not a tool;
the registry skips a stem beginning with `_`, and a tool imports from here and from no other tool
(tests/test_seams.py). What a column means, a statistic over a table or a linker's state belongs to
the tool that computes it, never here; how a table is drawn is `_draw.py`'s.

A table is a structured array, one record a region; its dtype carries the (height, width) of the
plane it was found in as metadata, `plane(table)`, so a tool relating it to a plane or table of
another shape can scale. `blobs` promises the position columns and the plane; any other column may
be NaN or absent where its producer did not make it. `contour` is an object column, (N, 2) x, y,
so the table is never a flat array.
"""
import math
from functools import lru_cache

import cv2
import numpy as np

DTYPE = np.dtype([("x", np.int32), ("y", np.int32), ("w", np.int32), ("h", np.int32), ("area", np.int32),
                  ("cx", np.float32), ("cy", np.float32), ("angle", np.float32),
                  ("major", np.float32), ("minor", np.float32),
                  ("mean", np.float32), ("peak", np.float32), ("core", np.int32), ("contour", object)])
TRACKS_DTYPE = np.dtype(DTYPE.descr + [("id", np.int32)])      # a tracks table of blobs' own columns
OUTLINES = ("box", "contour")


@lru_cache(maxsize=64)      # a tool asks at every row, and building a dtype of this many fields costs more than a threshold
def _plane_dtype(height, width, dtype):
    return np.dtype(dtype.descr, metadata={"plane": (height, width)})


def plane_dtype(shape, dtype=DTYPE):
    """`dtype` with the plane's (height, width) on it."""
    return _plane_dtype(int(shape[0]), int(shape[1]), dtype)


def plane(table):
    """The (height, width) the table was found in, or None when it has none."""
    return (table.dtype.metadata or {}).get("plane")


def is_table(row):
    """Whether a series' row is a table; False for a signal's value or a folded row."""
    return getattr(row, "dtype", None) is not None and row.dtype.names is not None


def is_tables(data):
    """Whether a series' rows are tables, read off the first; False for an empty series or a signal.
    A Series carries no type, so a tool over both reads the shape."""
    return len(data) > 0 and is_table(data[0])


def with_column(table, name, values):
    """The table with `values` as a column named `name`, the plane kept; a name the table already
    has raises ValueError, since overwriting a producer's column would silently change its meaning."""
    if name in table.dtype.names:
        raise ValueError(f"the table already has a column {name!r}")
    values = np.asarray(values)
    dtype = np.dtype(table.dtype.descr + [(name, values.dtype)], metadata=dict(table.dtype.metadata or {}))
    out = np.empty(len(table), dtype)
    for n in table.dtype.names:
        out[n] = table[n]
    out[name] = values
    return out


def moments(inside):
    """The centroid and moment ellipse of the set pixels of `inside`, a bool plane, as regionprops
    defines them: (cx, cy, angle, major, minor) in the plane's own pixels, angle in degrees from
    the x axis. At least one pixel must be set."""
    ys, xs = np.nonzero(inside)
    area = len(xs)
    xs, ys = xs.astype(np.float64), ys.astype(np.float64)
    cx, cy = xs.sum() / area, ys.sum() / area
    mu20, mu02, mu11 = (xs * xs).sum() / area - cx * cx, (ys * ys).sum() / area - cy * cy, (xs * ys).sum() / area - cx * cy
    half, spread = (mu20 + mu02) / 2, np.sqrt(4 * mu11 * mu11 + (mu20 - mu02) ** 2) / 2
    angle = np.degrees(0.5 * np.arctan2(2 * mu11, mu20 - mu02))
    return cx, cy, angle, 4 * np.sqrt(max(half + spread, 0)), 4 * np.sqrt(max(half - spread, 0))


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


def bound(text, default):
    """A bound knob's text as a float, `default` when it is blank, so a blank bound is none."""
    text = str(text).strip()
    return default if text == "" else float(text)
