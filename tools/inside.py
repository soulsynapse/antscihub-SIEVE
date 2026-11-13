"""Frame tool: which region each record of a table lies in, written onto the record; blobs in, a
second blobs table on `regions`, the first table out with the regions' columns added.

A record is in the region whose runs or filled contour, or box by `outline`, holds its centroid, the
regions placed in the first table's coordinates when the planes differ; in several it is in the
smallest by area, where attach joins the other way and takes the largest mark. The regions' `name`,
when they carry one, and the `columns` named, comma separated, land as `prefix`_name, with
`prefix`_n the regions the record is in; a record in none reads NaN in a numeric column and None in
a text one. A column the regions lack, or a name the first table already has, raises.
"""
import numpy as np

from tools._draw import draw as draw_table
from tools._table import OUTLINES, footprint, plane as plane_of, with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "inside", "frame", "blobs", "blobs"
INPUTS = {"regions": "blobs"}
LABEL = "name"
DEFAULTS = {"prefix": "region", "columns": "", "outline": "contour"}


def names(text):
    return [c.strip() for c in str(text).split(",") if c.strip()]


def is_text(dtype):
    return dtype.kind in "USO"


def inside(table, regions, prefix="region", columns=(), outline="contour"):
    shape = plane_of(table)
    if shape is None:
        raise ValueError("the first table carries no plane to place the regions in")
    other = plane_of(regions) or shape
    scale = (shape[0] / other[0], shape[1] / other[1])
    wanted = [*([LABEL] if LABEL in regions.dtype.names else []), *(c for c in columns if c != LABEL)]
    for c in wanted:
        if c not in regions.dtype.names:
            raise ValueError(f"inside: no column {c!r} on the regions; one of {regions.dtype.names}")
    labels, count = np.zeros(shape, np.int32), np.zeros(shape, np.int64)
    for i in np.argsort(-regions["area"].astype(np.float64), kind="stable"):
        rows, cols, held = footprint(regions[i], shape, scale, outline=outline)
        labels[rows, cols][held] = i + 1
        count[rows, cols][held] += 1
    px, py = np.floor(table["cx"] + 0.5).astype(int), np.floor(table["cy"] + 0.5).astype(int)
    on_plane = (px >= 0) & (px < shape[1]) & (py >= 0) & (py < shape[0])
    py, px = np.clip(py, 0, shape[0] - 1), np.clip(px, 0, shape[1] - 1)
    at = np.where(on_plane, labels[py, px], 0) - 1
    has = at >= 0
    out = table
    for c in wanted:
        if is_text(regions.dtype[c]):
            v = np.full(len(table), None, dtype=object)
            v[has] = [regions[c][k] for k in at[has]]
        else:
            v = np.full(len(table), np.nan)
            v[has] = regions[c][at[has]].astype(np.float64)
        out = with_column(out, f"{prefix}_{c}", v)
    return with_column(out, f"{prefix}_n", np.where(on_plane, count[py, px], 0))


def run(frames, row, params):
    return inside(frames(row), frames(row, "regions"), params["prefix"], names(params["columns"]), params["outline"])


def draw(painter, row, result, start, params):
    draw_table(painter, result, params.get("outline", "box"), color=(120, 200, 240))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_text("prefix", DEFAULTS["prefix"])
    w.add_text("columns", DEFAULTS["columns"])
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs, file, gray, region, threshold

    sys.exit(play([gray, threshold, blobs, file, region, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
