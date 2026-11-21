"""Frame tool: v2's change energy, the structure tensor's Jtt. Gray or mask in, a float32 plane out; zero where the
row before is absent, at row 0 and at the first row of a cut in time.

The frame-to-frame difference squared and Gaussian-blurred: the blur is the tensor's spatial window,
and v1 and v2 held it at sigma 2.0 as a constant. It is a knob here, with that default. The plane is in
gray units squared and is a measure, not an image; coarsegrain cells it and reduce makes it a signal.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "changeenergy", "frame", ("gray", "mask"), "gray"
PARAMS = {"sigma": {"default": 2.0, "kind": "float", "range": (0.5, 8.0), "decimals": 1}}


def reach_in_rows(params):
    return 1, 0


def run(frames, row, params):
    f, before = np.asarray(frames(row), np.float32), frames(row - 1)
    if before is None:
        return np.zeros_like(f)
    it = f - np.asarray(before, np.float32)
    return cv2.GaussianBlur(it * it, (0, 0), params["sigma"])


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
