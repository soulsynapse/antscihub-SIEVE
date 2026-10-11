"""Frame tool: resize gray frames by a factor."""
import cv2

from sieve_player import ParamWidget

NAME, KIND, EXPECTS, PRODUCES = "rescale", "frame", "gray", "gray"
DEFAULTS = {"scale": 0.5}


def run(frames, row, params):
    f = frames(row)
    s = params["scale"]
    return f if s == 1.0 else cv2.resize(f, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def settings(parent=None):
    w = ParamWidget(parent)
    w.add_float("scale", 0.1, 1.0, DEFAULTS["scale"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
