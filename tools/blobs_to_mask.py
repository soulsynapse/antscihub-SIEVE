"""Frame tool: a table's records painted into a mask the shape of the plane they were found in;
blobs in, mask out.

`outline` paints each record's runs or filled contour, or its box; a record with neither gets its
box either way, as draw shows it. No records is an empty mask. A table with no plane on it raises.
"""
import numpy as np

from tools._table import OUTLINES, footprint, plane

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "blobs-to-mask", "frame", "blobs", "mask"
DEFAULTS = {"outline": "contour"}


def mask(table, outline="contour"):
    shape = plane(table)
    if shape is None:
        raise ValueError("the table carries no plane to paint into")
    out = np.zeros(shape, np.uint8)
    for b in table:
        rows, cols, inside = footprint(b, shape, outline=outline)
        out[rows, cols][inside] = 255
    return out


def run(frames, row, params):
    return mask(frames(row), params["outline"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w
