"""Frame tool: what of the frame is narrower than a square and darker, or brighter, than its surround; gray or a mask in, gray out.

`mode` is the sign kept, as bg-subtract's: `darker`, the black top hat, the frame's closing less
the frame, an ant on a pale substrate; `brighter`, the white, the frame less its opening. The
square is of `radius` px about its centre, side 2 * radius + 1. A region the square does not fit
inside keeps its full depth however many neighbours it has; one it fits inside reads 0 where it
fits, so the square must be wider than the animal's body and a clump wider than the square keeps
only its limbs. Maxima and minima do not average noise, which reads as a floor of about twice its
deviation, rising with `radius`: `inner` is the radius of a box mean taken first, each mean rounded
to a whole level, 0 for none.
"""
import cv2

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "top-hat", "frame", ("gray", "mask"), "gray"
MODES = ("darker", "brighter")
OPS = {"darker": cv2.MORPH_BLACKHAT, "brighter": cv2.MORPH_TOPHAT}
MAX_RADIUS = 100
MAX_INNER = 15
PARAMS = {
    "mode": {"default": "darker", "kind": "choice", "choices": MODES},
    "radius": {"default": 15, "kind": "int", "range": (1, MAX_RADIUS)},
    "inner": {"default": 2, "kind": "int", "range": (0, MAX_INNER)},
}


def top_hat(frame, mode, radius, inner=0):
    if mode not in OPS:
        raise ValueError(f"top-hat: no mode {mode!r}; one of {MODES}")
    radius, inner = int(radius), int(inner)
    if radius < 1:
        raise ValueError(f"top-hat: radius {radius} must be at least 1")
    if inner:
        frame = cv2.blur(frame, (2 * inner + 1,) * 2)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2 * radius + 1,) * 2)
    return cv2.morphologyEx(frame, OPS[mode], kernel)


def run(frames, row, params):
    return top_hat(frames(row), params["mode"], params["radius"], params["inner"])


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
