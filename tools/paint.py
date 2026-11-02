"""Frame tool: a table's records painted into a mask the shape of the plane they were found in;
blobs in, mask out.

`outline` paints each record's contour filled or its box; a record with no contour gets its box
either way, as draw shows it. No records is an empty mask. A table with no plane on it raises.
"""
import cv2
import numpy as np

from tools.blobs import plane

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "paint", "frame", "blobs", "mask"
OUTLINES = ("contour", "box")
DEFAULTS = {"outline": "contour"}


def paint(table, outline="contour"):
    shape = plane(table)
    if shape is None:
        raise ValueError("the table carries no plane to paint into")
    out = np.zeros(shape, np.uint8)
    for b in table:
        contour = b["contour"] if outline == "contour" and "contour" in table.dtype.names else None
        if contour is None:
            out[b["y"]:b["y"] + b["h"], b["x"]:b["x"] + b["w"]] = 255
        else:
            cv2.fillPoly(out, [np.asarray(contour, np.int32).reshape(-1, 1, 2)], 255)
    return out


def run(frames, row, params):
    return paint(frames(row), params["outline"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w
