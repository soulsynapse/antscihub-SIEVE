"""Frame tool: the 8-connected regions of a mask's nonzero pixels, labelled by their runs; mask or gray in, blobs out.

blobs' knobs and columns, with `runs` where blobs has `contour`: the region's pixels as (N, 3)
y, x0, x1, x1 one past the run's last pixel, so a record's footprint is the region itself, holes
kept. Each row is cut into runs, a run joins those it touches in the row above, and area, box and
moments are sums over runs: no label plane is made and no region is read a pixel at a time, but
for the diff's columns. `split` is blobs' own.

The table's dtype, the plane on it and how a record meets a plane are tools/_table.py's.
"""
from tools._draw import draw as draw_table
from tools._runs import find
from tools._table import OUTLINES, RUNS_DTYPE as DTYPE

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "runs", "frame", ("mask", "gray"), "blobs"
INPUTS = {"diff": "gray"}
OPTIONAL = ("diff",)
DEFAULTS = {"min_area": 50, "max_area": 0, "core_threshold": 0, "split": False, "outline": "box"}
MAX_AREA = 100000


def run(frames, row, params):
    return find(frames(row), int(params["min_area"]), int(params["max_area"]), frames(row, "diff"),
                int(params["core_threshold"]), bool(params["split"]))


def draw(painter, row, result, start, params):
    draw_table(painter, result, params.get("outline", "box"))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("min_area", 0, MAX_AREA, DEFAULTS["min_area"])
    w.add_int("max_area", 0, MAX_AREA, DEFAULTS["max_area"])
    w.add_int("core_threshold", 0, 255, DEFAULTS["core_threshold"])
    w.add_bool("split", DEFAULTS["split"])
    w.add_choice("outline", OUTLINES, DEFAULTS["outline"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, threshold

    sys.exit(play([gray, threshold, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
