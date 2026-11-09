"""Frame tool: the frame cut to a rect read off a mask; a frame of any plane kind in, the mask on
`roi`, out as in at the cut's shape.

The rect is the bounding box of the roi's nonzero pixels at row 0, grown by `border` pixels each
way and clipped to the frame, so it is the same at every row under one key and a roi that moves
after row 0 moves nothing. A roi with no nonzero pixel at row 0 raises, as a frame of another
shape than the roi does, and the node says so. A mask cropped against itself is its own cut, so a
frame and the mask that bounded it meet downstream at one shape. `rect(roi, border)` is where the
cut sits on the frame, (y0, y1, x0, x1), the offset an export placing a table back on the plate
would add.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "crop", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
INPUTS = {"roi": "mask"}
DEFAULTS = {"border": 0}
MAX_BORDER = 500


def rect(roi, border=0):
    """(y0, y1, x0, x1) of the roi's nonzero pixels grown by `border` and clipped to the roi's
    shape; ValueError when no pixel is set."""
    ys, xs = np.nonzero(roi)
    if len(ys) == 0:
        raise ValueError("roi has no nonzero pixel at row 0; nothing to cut")
    h, w = roi.shape[:2]
    b = max(0, int(border))
    return max(int(ys.min()) - b, 0), min(int(ys.max()) + 1 + b, h), max(int(xs.min()) - b, 0), min(int(xs.max()) + 1 + b, w)


def run(frames, row, params):
    roi = frames(0, "roi")          # the memo holds row 0 of the roi, so this is a lookup, not a run
    y0, y1, x0, x1 = rect(roi, int(params["border"]))
    f = frames(row)
    if f.shape[:2] != roi.shape[:2]:
        raise ValueError(f"the frame is {f.shape[1]}x{f.shape[0]} and the roi {roi.shape[1]}x{roi.shape[0]}")
    return np.ascontiguousarray(f[y0:y1, x0:x1])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("border", 0, MAX_BORDER, DEFAULTS["border"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, threshold

    sys.exit(play([gray, threshold, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
