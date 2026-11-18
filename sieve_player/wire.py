"""What a wire carries: of each type its name, whether a row of it is a table, how its bytes are
counted and whether it can be overlaid, and the units a column of a table may be in. It names no
column: a tool mints one and says its unit there, through tools/_table.py. The player reads a
type here and never off a result's shape. It imports no Qt and nothing of the player, so a tool
may import it (tests/test_seams.py)."""
from typing import Callable, NamedTuple

import numpy as np


def own_bytes(v):
    """The bytes `v` itself holds: an array's own, 64 for anything else that is not None."""
    if v is None:
        return 0
    return v.nbytes if isinstance(v, np.ndarray) else 64


def table_bytes(v):
    """A table's own bytes and those of every array behind an object column of it, since
    `ndarray.nbytes` counts a contour as its eight-byte pointer."""
    if not isinstance(v, np.ndarray) or not v.dtype.names:
        return own_bytes(v)
    return v.nbytes + sum(own_bytes(x) for n in v.dtype.names if v.dtype[n] == object for x in v[n].ravel())


class Type(NamedTuple):
    table: bool         # a row of it is a table: a structured array, one record a region
    bytes: Callable     # what one row of it holds
    overlay: bool       # one plane the frame can be heated with


TYPES = {
    "bgr": Type(False, own_bytes, False),
    "gray": Type(False, own_bytes, True),
    "hsv": Type(False, own_bytes, False),
    "mask": Type(False, own_bytes, True),
    "flow": Type(False, own_bytes, False),
    "blobs": Type(True, table_bytes, False),
    "tracks": Type(True, table_bytes, False),
    "signal": Type(False, own_bytes, False),
    "path": Type(False, own_bytes, False),
}
ROWS = "rows"   # the field of a series node's result that holds its tables, one a row, where its type is a table

X, Y = "x", "y"                                                     # a position along x, along y
LENGTH_X, LENGTH_Y, LENGTH = "length x", "length y", "length"       # a length along x, along y, along neither
AREA = "area"
POINTS = "points"                                                   # an object column of (N, 2) x, y positions
UNITS = (X, Y, LENGTH_X, LENGTH_Y, LENGTH, AREA, POINTS)            # each of a plane's pixels
NONE = "none"   # said of a column in no plane's pixels; a column whose dtype says nothing was not said, or lost it


def is_table(type):
    """Whether a row of a wire of `type` is a table; False for a type the table does not have."""
    return type in TYPES and TYPES[type].table


def overlaid(type):
    return type in TYPES and TYPES[type].overlay


def nbytes(type, v):
    """The bytes one row `v` of a wire of `type` holds; its own for a type the table does not have,
    which is what a row folded, or a field of a result that is no table, is counted by."""
    return TYPES[type].bytes(v) if type in TYPES else own_bytes(v)


def share_bytes(type, share):
    """The bytes one row's share of a series node's result holds, the node producing `type`."""
    return sum(nbytes(type if f == ROWS else None, v) for f, v in share.items())


def result_bytes(type, result):
    """The bytes a series node's result over its rows holds, the node producing `type`: each field's
    own, and behind ROWS of a table type every table's."""
    tables = result[ROWS] if is_table(type) and ROWS in result else ()
    return sum(own_bytes(v) for v in result.values()) + sum(nbytes(type, t) for t in tables)
