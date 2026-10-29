"""Frame tool: |frame-to-frame difference|, gray or mask in, gray out; row 0 is all zero.

The difference is an image, not a number: what to make of it is downstream's choice (tools/reduce for a
per-row signal, tools/threshold for a mask of what moved, tools/downsample for a block mean).
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "motion", "frame", ("gray", "mask"), "gray"
DEFAULTS = {}


def run(frames, row, params):
    f = frames(row)
    return cv2.absdiff(f, frames(row - 1)) if row > 0 else np.zeros_like(f)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)   # no knobs


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
