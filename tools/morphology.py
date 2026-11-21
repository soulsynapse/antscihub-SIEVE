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
MAX_RADIUS = 15
PARAMS = {
    "method": {"default": "open", "kind": "choice", "choices": METHODS},
    "radius": {"default": 1, "kind": "int", "range": (1, MAX_RADIUS)},
    "iterations": {"default": 1, "kind": "int", "range": (1, 10)},
}


def morph(mask, method, radius, iterations):
    if method not in OPS:
        raise ValueError(f"no method {method!r}")
    side = 2 * int(radius) + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (side, side))
    return cv2.morphologyEx(mask, OPS[method], kernel, iterations=int(iterations))


def reach_in_rows(params):
    return 0, 0


def run(frames, row, params):
    return morph(frames(row), params["method"], params["radius"], params["iterations"])
