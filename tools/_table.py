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

A column's unit, one of sieve_player/wire.py's, is said where the column is minted, here or by
`with_column`, and rides the dtype as the plane does, `unit_of(table, column)`. A dtype made any
other way says nothing of its columns, and numpy drops the metadata with no error where it drops
it, so a reader takes a column unsaid as one that may have lost its unit, never as one in none.
"""
import math
from functools import lru_cache

import cv2
import numpy as np

from sieve_player.wire import AREA, LENGTH, LENGTH_X, LENGTH_Y, NONE, POINTS, UNITS, X, Y


def _said(unit, name):
    if unit not in UNITS and unit != NONE:
        raise ValueError(f"the column {name!r} has no unit {unit!r}; one of {(*UNITS, NONE)}")
    return unit


def dtype_of(columns):
    """A table's dtype of `columns`, each (name, type, unit) with the unit one of wire.UNITS or
    wire.NONE; ValueError, naming the column, for any other. It carries no plane."""
    return np.dtype([(n, t) for n, t, _ in columns], metadata={"units": {n: _said(u, n) for n, _, u in columns}})


def columns_of(dtype, names=None):
    """`dtype`'s columns as dtype_of takes them, those of `names` when given, in the dtype's order."""
    units = (dtype.metadata or {}).get("units", {})
    return [(n, dtype[n], units.get(n)) for n in dtype.names if names is None or n in names]


DTYPE = dtype_of([("x", np.int32, X), ("y", np.int32, Y), ("w", np.int32, LENGTH_X), ("h", np.int32, LENGTH_Y),
                  ("area", np.int32, AREA), ("cx", np.float32, X), ("cy", np.float32, Y), ("angle", np.float32, NONE),
                  ("major", np.float32, LENGTH), ("minor", np.float32, LENGTH),
                  ("mean", np.float32, NONE), ("peak", np.float32, NONE), ("core", np.int32, AREA), ("contour", object, POINTS)])
TRACKS_DTYPE = dtype_of(columns_of(DTYPE) + [("id", np.int32, NONE)])      # a tracks table of blobs' own columns
OUTLINES = ("box", "contour")


def _frozen(metadata):
    """What of a dtype's metadata its equality leaves out, hashable: two dtypes of the same fields
    are equal and hash alike whatever each says of them."""
    m = metadata or {}
    return tuple(sorted(m.get("units", {}).items())), tuple(sorted(m.get("planes", {}).items()))


@lru_cache(maxsize=64)      # a tool asks at every row, and building a dtype of this many fields costs more than a threshold
def _plane_dtype(height, width, dtype, said):
    return np.dtype(dtype.descr, metadata={**(dtype.metadata or {}), "plane": (height, width)})


def plane_dtype(shape, dtype=DTYPE):
    """`dtype` with the plane's (height, width) on it, what it says of its columns kept."""
    return _plane_dtype(int(shape[0]), int(shape[1]), dtype, _frozen(dtype.metadata))


def plane(table):
    """The (height, width) the table was found in, or None when it has none."""
    return (table.dtype.metadata or {}).get("plane")


def unit_of(table, column):
    """What the table's dtype says of `column`: (its unit, the plane it is of), the plane being the
    table's unless the column was minted of another, and None for a unit that is none; or None
    where the dtype says nothing of the column."""
    m = table.dtype.metadata or {}
    unit = m.get("units", {}).get(column)
    if unit is None:
        return None
    return unit, None if unit == NONE else m.get("planes", {}).get(column, m.get("plane"))


def is_table(row):
    """Whether a series' row is a table; False for a signal's value or a folded row."""
    return getattr(row, "dtype", None) is not None and row.dtype.names is not None


def is_tables(data):
    """Whether a series' rows are tables, read off the first; False for an empty series or a signal.
    A Series carries no type, so a tool over both reads the shape."""
    return len(data) > 0 and is_table(data[0])


def with_column(table, name, values, unit, of=None):
    """The table with `values` as a column named `name`, the plane and what is said of the other
    columns kept. `unit` is the column's, one of wire.UNITS or wire.NONE, and `of` the plane it is
    of where that is not the table's; a `unit` of None is a column copied from a table that said
    nothing of it, and nothing is said of it here. A name the table already has raises ValueError,
    since overwriting a producer's column would silently change its meaning."""
    if name in table.dtype.names:
        raise ValueError(f"the table already has a column {name!r}")
    values = np.asarray(values)
    m = dict(table.dtype.metadata or {})
    if unit is not None:
        m["units"] = {**m.get("units", {}), name: _said(unit, name)}
        if unit != NONE and of is not None and tuple(of) != m.get("plane"):
            m["planes"] = {**m.get("planes", {}), name: (int(of[0]), int(of[1]))}
    dtype = np.dtype(table.dtype.descr + [(name, values.dtype)], metadata=m)
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
