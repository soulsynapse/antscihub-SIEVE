"""Frame tool: binarize gray frames."""
import cv2

from sieve_player import ParamWidget

NAME, KIND, EXPECTS, PRODUCES = "threshold", "frame", "gray", "gray"
DEFAULTS = {"thresh": 128, "invert": False}


def run(frames, row, params):
    mode = cv2.THRESH_BINARY_INV if params["invert"] else cv2.THRESH_BINARY
    _, b = cv2.threshold(frames(row), params["thresh"], 255, mode)
    return b


def settings(parent=None):
    w = ParamWidget(parent)
    w.add_int("thresh", 0, 255, DEFAULTS["thresh"])
    w.add_bool("invert", DEFAULTS["invert"])
    return w
