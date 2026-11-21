"""Frame tool: the frame's mean over a small box less its mean over a large one; gray or a mask in, gray out.

The small box, of `inner` px about each pixel, smooths away what is finer than it, sensor noise
and texture; the large one, of `outer`, is the local background, so lighting and shading broader
than it cancel. What is left is structure between the two sizes, an animal when the boxes bracket
its width. `mode` is the sign kept, as bg-subtract's: `darker`, where the small mean is below the
background's, an ant on a pale substrate; `brighter`, the reverse; `absolute`, either. `outer` must
exceed `inner`. Each box's side is 2 * radius + 1, so neither shifts the image, and the frame's
edge is reflected to fill a box that runs past it.

`precision` is the width the means are held at. `32 bit` is the exact difference rounded once;
`16 bit` holds each mean to 1/256 of a level, so it rounds otherwise only where the exact value
lies within about 0.004 of a half level; `8 bit` rounds each mean to a whole level, so the output
can be a level off. Each is faster than the one before.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "box-bandpass", "frame", ("gray", "mask"), "gray"
MODES = ("darker", "brighter", "absolute")
PRECISIONS = ("8 bit", "16 bit", "32 bit")
MAX_RADIUS = 100
_WIDEN = np.arange(256, dtype=np.uint16) << 8
PARAMS = {
    "mode": {"default": "darker", "kind": "choice", "choices": MODES},
    "inner": {"default": 1, "kind": "int", "range": (0, MAX_RADIUS)},
    "outer": {"default": 15, "kind": "int", "range": (1, MAX_RADIUS)},
    "precision": {"default": "16 bit", "kind": "choice", "choices": PRECISIONS},
}


def _means(frame, inner, outer, precision):
    """The two means as one dtype, and the factor that takes their difference back to levels."""
    small, large = (2 * inner + 1,) * 2, (2 * outer + 1,) * 2
    if precision == "32 bit":
        return cv2.boxFilter(frame, cv2.CV_32F, small), cv2.boxFilter(frame, cv2.CV_32F, large), 1.0
    if precision == "16 bit":
        frame, scale = cv2.LUT(frame, _WIDEN), 1 / 256
    else:
        scale = 1.0
    return cv2.blur(frame, small), cv2.blur(frame, large), scale


def bandpass(frame, inner, outer, mode, precision="16 bit"):
    if mode not in MODES:
        raise ValueError(f"box-bandpass: no mode {mode!r}; one of {MODES}")
    if precision not in PRECISIONS:
        raise ValueError(f"box-bandpass: no precision {precision!r}; one of {PRECISIONS}")
    inner, outer = int(inner), int(outer)
    if outer <= inner:
        raise ValueError(f"box-bandpass: outer {outer} must exceed inner {inner}")
    fine, background, scale = _means(frame, inner, outer, precision)
    if mode == "absolute":
        d = cv2.absdiff(fine, background)
    else:
        d = cv2.subtract(background, fine) if mode == "darker" else cv2.subtract(fine, background)
        if d.dtype == np.float32:
            d = cv2.max(d, 0)      # the integer subtracts saturate at 0; a float one goes negative
    return cv2.convertScaleAbs(d, alpha=scale)


def reach_in_rows(params):
    return 0, 0


def run(frames, row, params):
    return bandpass(frames(row), params["inner"], params["outer"], params["mode"], params["precision"])


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
