"""Dummy: BGR to gray. Produces a flat gray frame of the input's size at `level`."""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "to_gray", "frame", "bgr", "gray"
DEFAULTS = {"level": 0}


def run(frames, row, params):
    return np.full(frames(row).shape[:2], params["level"], np.uint8)


def settings(parent=None):
    from sieve_player import ParamWidget

    w = ParamWidget(parent)
    w.add_int("level", 0, 255, DEFAULTS["level"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
