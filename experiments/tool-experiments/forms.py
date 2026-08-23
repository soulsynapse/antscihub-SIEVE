"""What a stored frame is, and when one already on hand can answer for another.

The session explorer's store is keyed by frame index and holds exactly one
shape, because the crop is a module-level global and a change to it wipes
everything derived from the old one. That is right for one consumer. With a
tool asking too, "hit" has to mean *the frame at this pts in a shape that
satisfies this request*, and the interesting cases are the ones where the
store holds something that is not the requested shape but contains it.

A form is three things: which source pixels (a rect in the source's own
coordinates, so it survives every downstream resampling), at what sampling
(the dimensions of the stored array, from which pixels-per-source-pixel
falls out), and in what pixel format. Everything else about a frame is
either its identity (the pts, per ADR-0004) or its content.

**The canonical construction.** Form *b* is built from a decoded source
frame by cropping `b.rect`, resizing to `b.out`, then converting to
`b.pix` — in that order, always. The order is part of the definition rather
than an optimisation left to the caller: converting to gray before the
resize is cheaper (one plane instead of three) and produces different bytes,
and a store in which two producers of "the same" form disagree in the low
bits is a store whose keys are lying. What the ordering costs is the
form-key experiment's to measure; that it is fixed is not negotiable.

**Domination has two grades, and only one of them may be admitted.** A form
*a* answers a request for *b* exactly when the derivation reproduces the
canonical construction byte for byte, which needs `a` to be at source
sampling over a rect containing `b`'s — then the sub-crop lands on integer
pixel boundaries and the remaining steps are `b`'s own. When `a` has already
been resampled (a display proxy, say), deriving `b` resamples twice and the
result is close but is not the frame: it is the explorer's `lo` route, and
it is a placeholder to look at while something better arrives.

So the admission rule, which is the law this module exists to state:
**derived is for looking at, decoded is for recording.** An approximate
derivation may be shown and must never be admitted to a store, written to a
series, or read by anything that commits. This is the same shape as the
explorer's rule that the GUI thread may block only for an exact request the
user just released — one level up, and for the same reason: the cheap answer
is allowed everywhere the expensive one has not arrived yet, and nowhere
that the answer is the product.

The exact grade also disposes of a hazard the domination idea otherwise
carries. If a request can be served from any of several dominating forms,
the bytes could depend on which happened to be cached, and the same
measurement would come out differently on a warm store than a cold one.
Restricted to exact derivations there is nothing to choose between: every
route to form *b* produces the same array, so cache state cannot reach a
result.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

#: pixel formats, and which can be produced from which. Dropping chroma is a
#: fixed matrix and therefore reproducible; inventing it is not.
_FROM = {"gray": {"gray"}, "bgr": {"gray", "bgr"}}

EXACT = "exact"      #: reproduces the canonical construction byte for byte
APPROX = "approx"    #: close enough to show, never close enough to keep


@dataclass(frozen=True)
class Form:
    """Which source pixels, at what sampling, in what format."""

    rect: tuple[int, int, int, int]   #: x, y, w, h in *source* pixels
    out: tuple[int, int]              #: w, h of the stored array
    pix: str                          #: "gray" | "bgr"

    @property
    def scale(self) -> tuple[float, float]:
        """Stored pixels per source pixel, x and y."""
        return self.out[0] / self.rect[2], self.out[1] / self.rect[3]

    @property
    def native(self) -> bool:
        """At source sampling — the grade that can be derived from exactly."""
        return self.out == (self.rect[2], self.rect[3])

    @property
    def nbytes(self) -> int:
        return self.out[0] * self.out[1] * (3 if self.pix == "bgr" else 1)

    def key(self) -> str:
        """The durable spelling, for a cache key or a coverage record.

        Source-pixel rect and output dimensions only: no reference to a
        window, a session or a canvas size, because a form outlives all
        three and a key that names them cannot be matched across runs.
        """
        x, y, w, h = self.rect
        return f"{x}+{y}+{w}x{h}@{self.out[0]}x{self.out[1]}:{self.pix}"


def source_form(width: int, height: int, pix: str = "bgr") -> Form:
    """The whole frame as decoded — what every other form derives from."""
    return Form((0, 0, width, height), (width, height), pix)


def build(frame: np.ndarray, form: Form) -> np.ndarray:
    """The canonical construction: crop, resize, convert, in that order.

    `frame` is a full decoded source frame in `form.pix`-compatible format.
    Every producer of a given form goes through here, which is what makes
    two of them agree.
    """
    x, y, w, h = form.rect
    out = frame[y:y + h, x:x + w]
    if (w, h) != form.out:
        interp = cv2.INTER_AREA if form.out[0] < w else cv2.INTER_LINEAR
        out = cv2.resize(out, form.out, interpolation=interp)
    if form.pix == "gray" and out.ndim == 3:
        out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    return np.ascontiguousarray(out)


def grade(have: Form, want: Form) -> str | None:
    """Can `have` answer for `want`, and how honestly?

    `None` means the region or the format is not there at any quality —
    the two refusals that no amount of resampling repairs. The two yeses
    are the admission fork: `EXACT` may be kept, `APPROX` may only be
    shown. How badly an `APPROX` falls short is `shortfall`'s to say.
    """
    if want.pix not in _FROM.get(have.pix, ()):
        return None
    hx, hy, hw, hh = have.rect
    wx, wy, ww, wh = want.rect
    if not (hx <= wx and hy <= wy and wx + ww <= hx + hw and wy + wh <= hy + hh):
        return None
    return EXACT if have.native else APPROX


def shortfall(have: Form, want: Form) -> float:
    """How much coarser `have` is than `want`, as a sampling ratio.

    1.0 or above means the pixels asked for are all present and the
    derivation only resamples; below it, the sampling is genuinely coarser
    and the difference is information that is not there — the explorer's
    `lo` route, upscaling a display proxy to fill a canvas.

    Both are `APPROX` and both are refused admission, so this does not
    reach the store's rules. It is here because the display path has a
    decision the store does not: a twice-resampled frame looks right and a
    four-times-upscaled one looks soft, and how soft a placeholder may be
    before showing nothing is better is a caller's floor to set, not a
    property of the forms.
    """
    hsx, hsy = have.scale
    wsx, wsy = want.scale
    return min(hsx / wsx, hsy / wsy)


def derive(arr: np.ndarray, have: Form, want: Form) -> tuple[np.ndarray, str]:
    """Produce `want` from an array already in `have`, with its grade.

    The exact path is the canonical construction with the crop rebased into
    `have`'s coordinates, so the bytes match a build from source. The
    approximate path is the same steps over pixels that have already been
    resampled once; it is offered because a placeholder now beats the truth
    in 300 ms, and it is labelled because nothing downstream may confuse
    the two.
    """
    how = grade(have, want)
    if how is None:
        raise ValueError(f"{have.key()} cannot answer for {want.key()}")
    hx, hy, _, _ = have.rect
    sx, sy = have.scale
    wx, wy, ww, wh = want.rect
    x0, y0 = round((wx - hx) * sx), round((wy - hy) * sy)
    x1, y1 = round((wx + ww - hx) * sx), round((wy + wh - hy) * sy)
    out = arr[y0:y1, x0:x1]
    if out.shape[1::-1] != want.out:
        interp = (cv2.INTER_AREA if out.shape[1] > want.out[0]
                  else cv2.INTER_LINEAR)
        out = cv2.resize(out, want.out, interpolation=interp)
    if want.pix == "gray" and out.ndim == 3:
        out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    return np.ascontiguousarray(out), how
