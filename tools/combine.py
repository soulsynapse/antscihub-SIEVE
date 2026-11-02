"""Frame tool: two masks as one; mask in, a second mask on `with`, mask out.

`method` is and, or, difference (the first less the second) or not, which reads the first alone
and lets `with` stay unwired. The masks must be one shape: a tool relating planes of two shapes
scales by the table between them, which a mask does not carry, so two shapes raise and the node
reports it.
"""
import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "combine", "frame", "mask", "mask"
INPUTS = {"with": "mask"}
OPTIONAL = ("with",)
METHODS = ("and", "or", "difference", "not")
DEFAULTS = {"method": "and"}


def combine(a, b, method):
    if method == "not":
        return cv2.bitwise_not(a)
    if b is None:
        raise ValueError(f"{method} needs a mask on with")
    if a.shape != b.shape:
        raise ValueError(f"masks of two shapes, {a.shape} and {b.shape}")
    if method == "and":
        return cv2.bitwise_and(a, b)
    if method == "or":
        return cv2.bitwise_or(a, b)
    if method == "difference":
        return cv2.bitwise_and(a, cv2.bitwise_not(b))
    raise ValueError(f"no method {method!r}")


def run(frames, row, params):
    method = params["method"]
    return combine(frames(row), None if method == "not" else frames(row, "with"), method)


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("method", METHODS, DEFAULTS["method"])
    return w
