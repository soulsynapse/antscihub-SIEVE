"""Frame tool: a frame let through a mask; a frame of any plane kind in, a mask on `mask`, out as in,
every pixel zero where the mask is and as it was elsewhere. The two must be one shape: two shapes
raise, as combine's do, and the node reports it.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "mask", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
INPUTS = {"mask": "mask"}
DEFAULTS = {}


def masked(frame, mask):
    if frame.shape[:2] != mask.shape[:2]:
        raise ValueError(f"the frame is {frame.shape[1]}x{frame.shape[0]} and the mask {mask.shape[1]}x{mask.shape[0]}")
    keep = mask != 0
    return np.where(keep if frame.ndim == 2 else keep[..., None], frame, np.zeros((), frame.dtype))


def run(frames, row, params):
    return masked(frames(row), frames(row, "mask"))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    return ParamWidget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, threshold

    sys.exit(play([gray, threshold, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
