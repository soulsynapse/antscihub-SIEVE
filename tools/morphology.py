"""Frame tool: open or close a mask; mask in, mask out.

`method` is open, which drops regions and protrusions thinner than the kernel, or close, which
fills gaps and holes thinner than it. The kernel is a square of `radius` px about its centre, so its
side is odd and the mask does not shift; `iterations` applies it that many times. Between
threshold and blobs it steadies an animal's area across rows and removes the specks blobs would
count and drop.
"""
import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "morphology", "frame", "mask", "mask"
METHODS = ("open", "close")
OPS = {"open": cv2.MORPH_OPEN, "close": cv2.MORPH_CLOSE}
DEFAULTS = {"method": "open", "radius": 1, "iterations": 1}
MAX_RADIUS = 15


def morph(mask, method, radius, iterations):
    if method not in OPS:
        raise ValueError(f"no method {method!r}")
    side = 2 * int(radius) + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (side, side))
    return cv2.morphologyEx(mask, OPS[method], kernel, iterations=int(iterations))


def run(frames, row, params):
    return morph(frames(row), params["method"], params["radius"], params["iterations"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("method", METHODS, DEFAULTS["method"])
    w.add_int("radius", 1, MAX_RADIUS, DEFAULTS["radius"])
    w.add_int("iterations", 1, 10, DEFAULTS["iterations"])
    return w
