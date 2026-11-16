"""Frame tool: the frame's mean over a small box less its mean over a large one; gray in, gray out.

The small box, of `inner` px about each pixel, smooths away what is finer than it, sensor noise
and texture; the large one, of `outer`, is the local background, so lighting and shading broader
than it cancel. What is left is structure between the two sizes, an animal when the boxes bracket
its width. `mode` is the sign kept, as bg-subtract's: `darker`, where the small mean is below the
background's, an ant on a pale substrate; `brighter`, the reverse; `absolute`, either. `outer` must
exceed `inner`. Each box's side is 2 * radius + 1, so neither shifts the image, and the frame's
edge is reflected to fill a box that runs past it.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "box-bandpass", "frame", "gray", "gray"
MODES = ("darker", "brighter", "absolute")
DEFAULTS = {"mode": "darker", "inner": 1, "outer": 15}
MAX_RADIUS = 100


def bandpass(frame, inner, outer, mode):
    if mode not in MODES:
        raise ValueError(f"box-bandpass: no mode {mode!r}; one of {MODES}")
    inner, outer = int(inner), int(outer)
    if outer <= inner:
        raise ValueError(f"box-bandpass: outer {outer} must exceed inner {inner}")
    f = frame.astype(np.float32)
    fine = cv2.blur(f, (2 * inner + 1,) * 2) if inner > 0 else f
    d = fine - cv2.blur(f, (2 * outer + 1,) * 2)
    if mode == "darker":
        d = -d
    elif mode == "absolute":
        d = np.abs(d)
    return np.clip(d, 0, 255).round().astype(np.uint8)


def run(frames, row, params):
    return bandpass(frames(row), params["inner"], params["outer"], params["mode"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("mode", MODES, DEFAULTS["mode"])
    w.add_int("inner", 0, MAX_RADIUS, DEFAULTS["inner"])
    w.add_int("outer", 1, MAX_RADIUS, DEFAULTS["outer"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play

    sys.exit(play([sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
