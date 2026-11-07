"""Frame tool: the frame against a background on its `bg` input, gray out; gray or BGR on either.

`mode` is the sign of the difference kept: `absolute`, either way; `darker`, where the frame is
darker than the background, an ant on a pale substrate; `brighter`, the reverse. A BGR difference
is taken per channel and the largest kept, so a change in any channel counts. A gray frame against
a BGR background, or the reverse, meets it in gray. `match_light` scales the frame so its mean
brightness is the background's before the difference, for a static composite under light that
drifts over the clip: without it the difference is the lighting, with it an animal.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "bg-subtract", "frame", ("gray", "bgr"), "gray"
INPUTS = {"bg": ("gray", "bgr")}
MODES = ("absolute", "darker", "brighter")
DEFAULTS = {"mode": "absolute", "match_light": False}


def _as_gray(a):
    return cv2.cvtColor(a, cv2.COLOR_BGR2GRAY) if a.ndim == 3 else a


def matched(frame, bg):
    """`frame` scaled so its mean is `bg`'s, clipped to the dtype; a black frame is left alone."""
    m = frame.mean()
    if m == 0:
        return frame
    return np.clip(frame * (bg.mean() / m), 0, 255).round().astype(frame.dtype)


def difference(frame, bg, mode, match_light=False):
    if mode not in MODES:
        raise ValueError(f"bg-subtract: no mode {mode!r}; one of {MODES}")
    if frame.ndim != bg.ndim:
        frame, bg = _as_gray(frame), _as_gray(bg)
    if match_light:
        frame = matched(frame, bg)
    if mode == "absolute":
        d = cv2.absdiff(frame, bg)
    elif mode == "darker":
        d = cv2.subtract(bg, frame)
    else:
        d = cv2.subtract(frame, bg)
    return d.max(axis=2) if d.ndim == 3 else d


def run(frames, row, params):
    return difference(frames(row), frames(row, "bg"), params["mode"], params["match_light"])


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_choice("mode", MODES, DEFAULTS["mode"])
    w.add_bool("match_light", DEFAULTS["match_light"])
    return w


if __name__ == "__main__":
    import os
    import sys
    import tempfile

    from sieve_player import document, play
    from tools import background, gray

    me = sys.modules[__name__]
    doc = document.from_tools([gray, background, me], sys.argv[1] if len(sys.argv) > 1 else None)
    doc.connect("gray", NAME)                       # from_tools wired the nearest producer, background, into "in"
    doc.connect("background", NAME, "bg")
    doc.display = NAME
    path = os.path.join(tempfile.mkdtemp(), "bg-subtract.json")
    document.save(doc, path)
    sys.exit(play(path, tools=[gray, background, me]))
