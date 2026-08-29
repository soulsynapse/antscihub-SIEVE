"""What a frame is, and who shapes one.

A form is which source pixels, at what sampling, in what pixel format. The
rect is in the source's own coordinates so it survives every downstream
resampling.

**The construction lives here, not in any tool.** A form vocabulary exists so
that two producers of one form agree byte for byte; a canonical construction
copied into each tool is exactly two producers that will not. The tool
decodes, the contract shapes.

**Domination has two grades and only one may be admitted.** A form on hand
answers a request exactly when it is at source sampling over a rect
containing the wanted one — then the sub-crop lands on integer boundaries.
Anything already resampled resamples twice: showable, never storable.

`build` refuses to resample, deliberately. Which resampler is canonical is a
real decision — INTER_AREA, swscale and a decoder's own scaler give three
different arrays — and it belongs with whoever builds the store and the proxy
tier. Gray is BT.601 in OpenCV's fixed point, so this and `cv2.cvtColor`
agree; the agreement is a convenience, and this function is the authority.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

#: Which format can be produced from which. Dropping chroma is a fixed matrix
#: and reproducible; inventing it is not.
_FROM = {"gray": {"gray"}, "bgr": {"gray", "bgr"}}

EXACT = "exact"      #: reproduces the canonical construction byte for byte
APPROX = "approx"    #: close enough to show, never close enough to keep

# BT.601 luma in OpenCV's fixed point: 14-bit shift, round-to-nearest.
_R2Y, _G2Y, _B2Y, _ROUND, _SHIFT = 4899, 9617, 1868, 1 << 13, 14


@dataclass(frozen=True)
class Form:
    """Which source pixels, at what sampling, in what format."""

    rect: tuple[int, int, int, int]   #: x, y, w, h in *source* pixels
    out: tuple[int, int]              #: w, h of the delivered array
    pix: str                          #: "gray" | "bgr"

    @property
    def scale(self) -> tuple[float, float]:
        return self.out[0] / self.rect[2], self.out[1] / self.rect[3]

    @property
    def native(self) -> bool:
        """At source sampling — the grade that can be derived from exactly."""
        return self.out == (self.rect[2], self.rect[3])

    @property
    def nbytes(self) -> int:
        return self.out[0] * self.out[1] * (3 if self.pix == "bgr" else 1)

    def key(self) -> str:
        """The durable spelling. Source-pixel rect and output dimensions
        only — a form outlives any window, session or canvas, and a key
        naming one cannot be matched across runs."""
        x, y, w, h = self.rect
        return f"{x}+{y}+{w}x{h}@{self.out[0]}x{self.out[1]}:{self.pix}"


def source_form(width: int, height: int, pix: str = "bgr") -> Form:
    """The whole frame as decoded — what every other form derives from."""
    return Form((0, 0, width, height), (width, height), pix)


def grade(have: Form, want: Form) -> str | None:
    """Can `have` answer for `want`, and how honestly?

    `None` is the refusal no resampling repairs: the region or the format is
    not there. `EXACT` may be kept, `APPROX` may only be shown.
    """
    if want.pix not in _FROM.get(have.pix, ()):
        return None
    hx, hy, hw, hh = have.rect
    wx, wy, ww, wh = want.rect
    if not (hx <= wx and hy <= wy and wx + ww <= hx + hw and wy + wh <= hy + hh):
        return None
    return EXACT if have.native else APPROX


def build(frame: np.ndarray, want: Form) -> np.ndarray:
    """Crop then convert, in that order, from a whole decoded frame.

    Order is part of the definition rather than a caller's choice: a
    construction that is a convention is one two producers eventually read
    differently.
    """
    if not want.native:
        raise NotImplementedError(
            f"{want.key()} needs resampling; no canonical resampler is chosen"
        )
    x, y, w, h = want.rect
    out = frame[y:y + h, x:x + w]
    if want.pix == "gray" and out.ndim == 3:
        blue = out[..., 0].astype(np.uint32)
        green = out[..., 1].astype(np.uint32)
        red = out[..., 2].astype(np.uint32)
        out = ((red * _R2Y + green * _G2Y + blue * _B2Y + _ROUND)
               >> _SHIFT).astype(np.uint8)
    elif want.pix == "bgr" and out.ndim == 2:
        raise ValueError("cannot invent chroma: gray cannot answer for bgr")
    return np.ascontiguousarray(out)
