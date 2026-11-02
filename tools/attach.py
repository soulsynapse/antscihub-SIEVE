"""Frame tool: the records of a second table written onto the records of the first they sit on;
blobs in, a second blobs table on `marks`, the first table out with the second's columns added.

A mark attaches to the record of the first table whose filled contour, or box by `outline`, holds
its centroid, placed in the first table's coordinates when the planes differ. Its `cx`, `cy` and
`area` and the `columns` named, comma separated, land as `prefix`_name, cx and cy in the first
table's coordinates, area in the mark's own pixels, with `prefix`_n the marks on the record; a
record under none reads NaN and 0, one under several reads the largest by area. A column named
that the second table lacks, a non-numeric one, or a name the first already has, raises.
"""
import numpy as np

from tools.blobs import plane as plane_of, with_column
from tools.paint import OUTLINES, footprint

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "attach", "frame", "blobs", "blobs"
INPUTS = {"marks": "blobs"}
ALWAYS = ("cx", "cy", "area")
DEFAULTS = {"prefix": "mark", "columns": "", "outline": "contour"}


def names(text):
    return [c.strip() for c in str(text).split(",") if c.strip()]


def attach(table, marks, prefix="mark", columns=(), outline="contour"):
    shape = plane_of(table)
    if shape is None:
        raise ValueError("the first table carries no plane to place the marks in")
    other = plane_of(marks) or shape
    sy, sx = shape[0] / other[0], shape[1] / other[1]
    wanted = [*ALWAYS, *(c for c in columns if c not in ALWAYS)]
    for c in wanted:
        if c not in marks.dtype.names or marks.dtype[c] == object:
            raise ValueError(f"attach: no numeric column {c!r} on the marks; one of {tuple(n for n in marks.dtype.names if marks.dtype[n] != object)}")
    labels = np.zeros(shape, np.int32)
    for i, b in enumerate(table):
        rows, cols, inside = footprint(b, shape, outline=outline)
        labels[rows, cols][inside] = i + 1
    mx, my = (marks["cx"] + 0.5) * sx - 0.5, (marks["cy"] + 0.5) * sy - 0.5
    px, py = np.floor(mx + 0.5).astype(int), np.floor(my + 0.5).astype(int)
    held = (px >= 0) & (px < shape[1]) & (py >= 0) & (py < shape[0])
    on = np.where(held, labels[np.clip(py, 0, shape[0] - 1), np.clip(px, 0, shape[1] - 1)], 0) - 1
    count = np.bincount(on[on >= 0], minlength=len(table)).astype(np.int64)
    pick = np.full(len(table), -1)
    for j in np.argsort(marks["area"], kind="stable"):
        if on[j] >= 0:
            pick[on[j]] = j
    out = table
    for c in wanted:
        v = np.full(len(table), np.nan)
        has = pick >= 0
        v[has] = marks[c][pick[has]].astype(np.float64)
        if c == "cx":
            v[has] = mx[pick[has]]
        elif c == "cy":
            v[has] = my[pick[has]]
        out = with_column(out, f"{prefix}_{c}", v)
    return with_column(out, f"{prefix}_n", count)


def run(frames, row, params):
    return attach(frames(row), frames(row, "marks"), params["prefix"], names(params["columns"]), params["outline"])


def draw(painter, row, result, start, params):
    from tools import blobs

    blobs.draw(painter, row, result, start, params, color=(240, 120, 200))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_text("prefix", DEFAULTS["prefix"])
    w.add_text("columns", DEFAULTS["columns"])
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w
