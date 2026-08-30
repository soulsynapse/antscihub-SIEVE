"""What a frame is, and who shapes one.

A form is which source pixels, at what sampling, in what pixel format. The
rect is in the source's own coordinates so it survives every downstream
resampling.

**The tool decodes, the contract shapes — and the split is exactly there.**
Which source pixels and at what sampling is this module's, because a rect
copied into each tool is two tools that will crop differently. What a pixel
*is* belongs to whoever produced it: a decoder that already holds luma hands
over luma, and this crops it.

That is narrower than what this file used to claim, and the narrowing is the
one correction experiment forced. The gray construction below was written
from argument and never run; the session explorer took the decoder's plane
and every measured number on the storage shelf came out of frames that did.
Serving the plane instead of reconstructing gray from BGR is the difference
between a crop and a whole-frame colour conversion — 8 ms against 18.7 on the
footage in `video-tests/`. Where two producers of one form disagree in the low
bits, they disagree because they are different instruments, and a construction
here that overrode both would only hide it.

**Domination has two grades and only one may be admitted.** A form on hand
answers a request exactly when it is at source sampling over a rect
containing the wanted one — then the sub-crop lands on integer boundaries.
Anything already resampled resamples twice: showable, never storable. That
is the rule `experiments/tool-experiments/forms.py` states as *derived is for
looking at, decoded is for recording*, and it is about the frame on hand and
not about the wanted one: a downscale from source sampling reproduces the
construction and is `EXACT`, which is what makes a display proxy something a
tier can be built on rather than a picture that may only be glanced at.

**The canonical construction is crop, resize, convert, in that order.** The
order is part of the definition and not a caller's choice: converting to gray
before resizing is cheaper, produces different bytes, and a store where two
producers of one form disagree in the low bits has keys that lie.

`build` used to refuse the resize, and that refusal is what a display proxy
broke against — a proxy form is resampled by definition, so nothing could
produce one and the tier had no bottom. Which resampler is canonical was the
real decision behind the refusal and it is settled here: swscale's `AREA`
downscaling and `BILINEAR` up. Not OpenCV's, which is what the oracle above
used, for the reason the gray branch below is hand-written rather than
imported — cv2 is not a dependency of the substrate. And swscale rather than
any other because a proxy *file* is written by a decoder's own scaler, so
this is the choice under which the file and the construction agree.

The gray branch is BT.601 in OpenCV's fixed point, which is what a producer
that holds only colour pixels falls back to; a producer that holds luma
serves it and passes through the crop alone.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import av
import numpy as np
from av.video.reformatter import Interpolation, VideoReformatter

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


def derive(frame: np.ndarray, have: Form, want: Form) -> np.ndarray:
    """Produce *want* from an array already in *have*, not from a source frame.

    `build` starts from a whole decoded frame at source sampling; this starts
    from one that is already some other form, so the wanted rect has to be
    rebased into the coordinates the array is actually in. The steps after
    that are the same three in the same order.

    **What comes out is for looking at and never for keeping** where *have* is
    not native — which is the only case anything calls this for today, the
    display proxy. `grade` says which it is; the rule is enforced by the tier
    that calls this never writing the result to the store, because a proxy
    pixel admitted once is a wrong pixel under a right key forever.
    """
    hx, hy, _, _ = have.rect
    sx, sy = have.scale
    wx, wy, ww, wh = want.rect
    x0, y0 = round((wx - hx) * sx), round((wy - hy) * sy)
    x1, y1 = round((wx + ww - hx) * sx), round((wy + wh - hy) * sy)
    out = frame[y0:y1, x0:x1]
    if not out.size:
        raise ValueError(f"{have.key()} holds none of {want.key()}")
    if out.shape[1::-1] != want.out:
        out = _resample(out, want.out)
    if want.pix == "gray" and out.ndim == 3:
        out = _luma(out)
    elif want.pix == "bgr" and out.ndim == 2:
        raise ValueError("cannot invent chroma: gray cannot answer for bgr")
    return np.ascontiguousarray(out)


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


#: One reformatter per thread. `to_ndarray(format=...)` builds and frees an
#: SwsContext per call — 49x of pure setup on a small frame
#: (`docs/findings/2026.08.21-pyav-to-ndarray-pays-sws-setup-per-call.md`) —
#: and one shared across threads would be a scaler two callers reconfigure
#: under each other. The fill thread and the drawing thread both build forms.
_LOCAL = threading.local()


def _resample(out: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """*out* at *size*, through swscale. `AREA` down and `BILINEAR` up.

    `AREA` and not the default bilinear because bilinear undersamples on the
    way down and aliases: a proxy of a moving animal built with it shimmers,
    which is the artefact `AREA` exists to remove. Up is bilinear because
    there is nothing to average.
    """
    reformatter = getattr(_LOCAL, "reformatter", None)
    if reformatter is None:
        reformatter = _LOCAL.reformatter = VideoReformatter()
    fmt = "gray" if out.ndim == 2 else "bgr24"
    frame = av.VideoFrame.from_ndarray(np.ascontiguousarray(out), format=fmt)
    return reformatter.reformat(
        frame, width=size[0], height=size[1], format=fmt,
        interpolation=(Interpolation.AREA if size[0] < out.shape[1]
                       else Interpolation.BILINEAR),
    ).to_ndarray()


def _luma(out: np.ndarray) -> np.ndarray:
    """BT.601 in OpenCV's fixed point — what a producer holding only colour
    falls back to. One that holds the decoder's luma plane serves that."""
    blue = out[..., 0].astype(np.uint32)
    green = out[..., 1].astype(np.uint32)
    red = out[..., 2].astype(np.uint32)
    return ((red * _R2Y + green * _G2Y + blue * _B2Y + _ROUND)
            >> _SHIFT).astype(np.uint8)


def build(frame: np.ndarray, want: Form) -> np.ndarray:
    """Crop, resize, convert, in that order, from a whole decoded frame.

    Order is part of the definition rather than a caller's choice: a
    construction that is a convention is one two producers eventually read
    differently.
    """
    x, y, w, h = want.rect
    out = frame[y:y + h, x:x + w]
    if (w, h) != want.out:
        out = _resample(out, want.out)
    if want.pix == "gray" and out.ndim == 3:
        out = _luma(out)
    elif want.pix == "bgr" and out.ndim == 2:
        raise ValueError("cannot invent chroma: gray cannot answer for bgr")
    return np.ascontiguousarray(out)
