"""What a stored frame is, and when one on hand can answer for another.

A form is which source pixels, at what sampling, in what pixel format. The
rect is in the source's own coordinates so it survives every downstream
resampling; the output dimensions give pixels-per-source-pixel; the format
says what a channel means. Everything else about a frame is either its
identity — the pts, per ADR-0004 — or its content.

**The canonical construction is fixed.** A form is built from a decoded
source frame by cropping its rect, resizing to its output dimensions, then
converting its format, in that order, always. The order is part of the
definition rather than a choice left to a caller: converting to gray before
resizing is cheaper, produces different bytes, and a store in which two
producers of one form disagree in the low bits has keys that lie.

**Domination has two grades and only one may be admitted.** A form answers a
request exactly when the derivation reproduces that construction byte for
byte, which needs the form on hand to be at source sampling over a rect
containing the wanted one — then the sub-crop lands on integer boundaries
and the remaining steps are the wanted form's own. Anything already
resampled resamples twice, and the result is close without being the frame.

So the law this module exists to state: **derived is for looking at, decoded
is for recording.** An approximate derivation may be shown and must never be
admitted to a store, written to a series, or read by anything that commits.
It is the same shape as the rule that a GUI thread may block only for a
request the user just released — the cheap answer is allowed everywhere the
expensive one has not arrived, and nowhere that the answer is the product.

The exact grade also removes a hazard the idea otherwise carries. If a
request could be served from any of several dominating forms, the bytes
would depend on which happened to be cached, and a measurement would come
out differently warm than cold. Restricted to exact derivations there is
nothing to choose between: every route to a form produces the same array, so
cache state cannot reach a result.

Whether deriving is worth preferring over decoding again is not assumed
here — it depends on what the decode costs, and
`experiments/tool-experiments/02-form-derivation.py` measured it against
both regimes the loop runs in. Its answer inverts between them: derivation
pays only where decode is expensive, which is exactly where the dominating
form is too heavy to hold much of. So the domination test belongs to the
hunt tier, and the window tier keeps the wipe it already has — which is why
`grade` is offered here and not applied everywhere by default.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

#: pixel formats, and which can be produced from which. Dropping chroma is a
#: fixed matrix and reproducible; inventing it is not.
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

        Source-pixel rect and output dimensions only. No reference to a
        window, a session or a canvas size, because a form outlives all
        three and a key naming them cannot be matched across runs.
        """
        x, y, w, h = self.rect
        return f"{x}+{y}+{w}x{h}@{self.out[0]}x{self.out[1]}:{self.pix}"


def source_form(width: int, height: int, pix: str = "bgr") -> Form:
    """The whole frame as decoded — what every other form derives from."""
    return Form((0, 0, width, height), (width, height), pix)


def build(frame: np.ndarray, form: Form) -> np.ndarray:
    """The canonical construction: crop, resize, convert, in that order.

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
    the two refusals no amount of resampling repairs. The two yeses are the
    admission fork: `EXACT` may be kept, `APPROX` may only be shown. How
    badly an `APPROX` falls short is `shortfall`'s to say.
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

    At or above one, every pixel asked for is present and a derivation only
    resamples. Below it the sampling is genuinely coarser and the difference
    is information that is not there.

    Both are `APPROX` and both are refused admission, so this reaches none
    of the store's rules. It exists because the display has a decision the
    store does not: a twice-resampled frame looks right and a heavily
    upscaled one looks soft, and how soft a placeholder may be before
    showing nothing is better is a caller's floor to set.
    """
    hsx, hsy = have.scale
    wsx, wsy = want.scale
    return min(hsx / wsx, hsy / wsy)


def derive(arr: np.ndarray, have: Form, want: Form) -> tuple[np.ndarray, str]:
    """Produce `want` from an array already in `have`, with its grade.

    The exact path is the canonical construction with the crop rebased into
    the source form's coordinates, so the bytes match a build from source.
    The approximate path is the same steps over pixels already resampled
    once; it is offered because a placeholder now beats the truth later, and
    it is labelled because nothing downstream may confuse the two.
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
