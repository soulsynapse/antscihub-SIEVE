"""Frame tool, experimental: the regions where a frame differs from a background by more than a cut, labelled
by their runs; gray in, a gray background on `bg`, blobs out.

bg-subtract, threshold and runs in one node, the three's knobs under the three's names: `mode` is the
sign of the difference kept, `thresh` the cut on it. The difference and the mask are made and dropped
inside the run, so neither can be shown or wired on, and `mean`, `peak` and `core` are not made. It is
here for what a clip walk costs, docs/findings/2026-11-13-sieve-against-the-trex-port.md; the three
nodes are the ones to tune with.
"""
import cv2

from tools._draw import draw as draw_table
from tools._runs import find
from tools._table import OUTLINES, RUNS_DTYPE as DTYPE

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "segment", "frame", "gray", "blobs"
INPUTS = {"bg": "gray"}
MODES = ("absolute", "darker", "brighter")
DEFAULTS = {"mode": "absolute", "thresh": 128, "min_area": 50, "max_area": 0, "outline": "box"}
MAX_AREA = 100000


def regions(frame, bg, mode, thresh, min_area, max_area=0):
    if mode not in MODES:
        raise ValueError(f"segment: no mode {mode!r}; one of {MODES}")
    d = cv2.absdiff(frame, bg) if mode == "absolute" else cv2.subtract(bg, frame) if mode == "darker" else cv2.subtract(frame, bg)
    return find(cv2.threshold(d, thresh, 255, cv2.THRESH_BINARY)[1], min_area, max_area)


def run(frames, row, params):
    return regions(frames(row), frames(row, "bg"), params["mode"], int(params["thresh"]),
                   int(params["min_area"]), int(params["max_area"]))


def draw(painter, row, result, start, params):
    draw_table(painter, result, params.get("outline", "box"))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("mode", MODES, DEFAULTS["mode"])
    w.add_int("thresh", 0, 255, DEFAULTS["thresh"])
    w.add_int("min_area", 0, MAX_AREA, DEFAULTS["min_area"])
    w.add_int("max_area", 0, MAX_AREA, DEFAULTS["max_area"])
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import background, gray

    sys.exit(play([gray, background, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
