"""Dummy: expects a tuple of types, produces gray. Zeros of the input's height and width."""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "either", "frame", ("bgr", "gray"), "gray"
DEFAULTS = {"scale": 1.0}


def run(frames, row, params):
    h, w = frames(row).shape[:2]
    s = params["scale"]
    return np.zeros((max(1, int(h * s)), max(1, int(w * s))), np.uint8)


def settings(parent=None):
    from sieve_player import ParamWidget

    w = ParamWidget(parent)
    w.add_float("scale", 0.1, 1.0, DEFAULTS["scale"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
