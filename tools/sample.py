"""Frame tool: a statistic of a plane inside each record, as a column; blobs in, a gray or mask
plane on `plane`, blobs out with `column` added.

`method` is mean, max or count (nonzero pixels), read within the record's filled contour, not its
box. A plane of another shape than the table's is read in the plane's coordinates, the record
scaled by the ratio of the shapes, so count is in the plane's pixels. A record whose footprint is
empty reads NaN, or 0 for count. The table must carry a plane and must not already have `column`.
"""
import numpy as np

from tools._draw import draw as draw_table
from tools._table import footprint, plane as plane_of, with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "sample", "frame", "blobs", "blobs"
INPUTS = {"plane": ("gray", "mask")}
METHODS = ("mean", "max", "count")
DEFAULTS = {"column": "sample", "method": "mean"}


def sample(table, plane, column, method="mean"):
    if method not in METHODS:
        raise ValueError(f"sample: no method {method!r}; one of {METHODS}")
    shape = plane_of(table)
    if shape is None:
        raise ValueError("the table carries no plane to scale by")
    scale = (plane.shape[0] / shape[0], plane.shape[1] / shape[1])
    out = np.zeros(len(table), np.int64 if method == "count" else np.float32)
    for k, b in enumerate(table):
        rows, cols, inside = footprint(b, plane.shape, scale)
        v = plane[rows, cols][inside]
        if method == "count":
            out[k] = np.count_nonzero(v)
        elif len(v) == 0:
            out[k] = np.nan
        else:
            out[k] = v.mean() if method == "mean" else v.max()
    return with_column(table, column, out)


def run(frames, row, params):
    return sample(frames(row), frames(row, "plane"), params["column"], params["method"])


def draw(painter, row, result, start, params):
    draw_table(painter, result, params.get("outline", "box"), color=(120, 180, 240))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_text("column", DEFAULTS["column"])
    w.add_choice("method", METHODS, DEFAULTS["method"])
    return w
