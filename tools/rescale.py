"""Frame tool: resize frames by a factor; BGR, gray or mask, out as in."""
import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "rescale", "frame", ("bgr", "gray", "mask"), "same"
DEFAULTS = {"scale": 0.5}


def run(frames, row, params):
    f = frames(row)
    s = params["scale"]
    return f if s == 1.0 else cv2.resize(f, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_float("scale", 0.1, 1.0, DEFAULTS["scale"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
