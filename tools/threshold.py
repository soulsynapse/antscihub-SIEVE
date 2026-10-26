"""Frame tool: binarize gray frames with one cut. For a color band use tools/inrange."""
import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "threshold", "frame", "gray", "gray"
DEFAULTS = {"thresh": 128, "invert": False}


def run(frames, row, params):
    mode = cv2.THRESH_BINARY_INV if params["invert"] else cv2.THRESH_BINARY
    _, b = cv2.threshold(frames(row), params["thresh"], 255, mode)
    return b


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("thresh", 0, 255, DEFAULTS["thresh"])
    w.add_bool("invert", DEFAULTS["invert"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
