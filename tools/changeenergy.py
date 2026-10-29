"""Frame tool: v2's change energy, the structure tensor's Jtt. Gray or mask in, a float32 plane out; row 0 is zero.

The frame-to-frame difference squared and Gaussian-blurred: the blur is the tensor's spatial window,
and v1 and v2 held it at sigma 2.0 as a constant. It is a knob here, with that default. The plane is in
gray units squared and is a measure, not an image; coarsegrain cells it and reduce makes it a signal.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "changeenergy", "frame", ("gray", "mask"), "gray"
DEFAULTS = {"sigma": 2.0}


def run(frames, row, params):
    f = np.asarray(frames(row), np.float32)
    if row == 0:
        return np.zeros_like(f)
    it = f - np.asarray(frames(row - 1), np.float32)
    return cv2.GaussianBlur(it * it, (0, 0), params["sigma"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_float("sigma", 0.5, 8.0, DEFAULTS["sigma"], decimals=1)
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
