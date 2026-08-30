"""What a frame is, and who shapes one.

Rect is in source coordinates so it survives downstream resampling. The
canonical construction is crop, resize, convert — order is part of the
definition, not a caller's choice. A native form (source sampling) is EXACT
and storable; a resampled one is APPROX and may only be shown.

**The sample format is part of the form, and that is what admits a field.**
Geometry alone cannot tell a float32 measurement from the gray frame it was
measured on: same rect, same size, and `grade` would call one EXACT for the
other while `Form.key` filed both under one name. Spelling the format keeps
the two apart in the two places that decide — the grade and the key a durable
record is folded from — which is what `edges.FIELD` rests on.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

import av
import numpy as np
from av.video.reformatter import Interpolation, VideoReformatter

#: Which format can be produced from which. Dropping chroma is a fixed matrix
#: and reproducible; inventing it is not.
#:
#: `f32` — a measurement per pixel — is absent from both sides on purpose, so
#: `grade` answers None in either direction between a field and a picture. A
#: measurement resampled averages quantities, which is a different measurement
#: rather than a coarser view of the same one, and a picture is not a
#: measurement at all. A field want is matched by form equality.
_FROM = {"gray": {"gray"}, "bgr": {"gray", "bgr"}}

#: Bytes per sample, per format. A field is float32 and costs four.
_WIDTH = {"gray": 1, "bgr": 3, "f32": 4}

EXACT = "exact"      #: reproduces the canonical construction byte for byte
APPROX = "approx"    #: close enough to show, never close enough to keep

# BT.601 luma in OpenCV's fixed point: 14-bit shift, round-to-nearest.
_R2Y, _G2Y, _B2Y, _ROUND, _SHIFT = 4899, 9617, 1868, 1 << 13, 14


@dataclass(frozen=True)
class Form:
    """Which source pixels, at what sampling, in what format."""

    rect: tuple[int, int, int, int]   #: x, y, w, h in *source* pixels
    out: tuple[int, int]              #: w, h of the delivered array
    pix: str                          #: "gray" | "bgr" | "f32"

    @property
    def scale(self) -> tuple[float, float]:
        return self.out[0] / self.rect[2], self.out[1] / self.rect[3]

    @property
    def native(self) -> bool:
        """At source sampling — the grade that can be derived from exactly."""
        return self.out == (self.rect[2], self.rect[3])

    @property
    def nbytes(self) -> int:
        return self.out[0] * self.out[1] * _WIDTH[self.pix]

    def key(self) -> str:
        """Durable spelling — no session-local state, matchable across runs."""
        x, y, w, h = self.rect
        return f"{x}+{y}+{w}x{h}@{self.out[0]}x{self.out[1]}:{self.pix}"


def source_form(width: int, height: int, pix: str = "bgr") -> Form:
    """The whole frame as decoded — what every other form derives from."""
    return Form((0, 0, width, height), (width, height), pix)


def derive(frame: np.ndarray, have: Form, want: Form) -> np.ndarray:
    """Produce *want* from an array already in *have*'s form.

    Result is APPROX when *have* is not native — showable, never storable.
    """
    _not_a_measurement(have, want)
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


def _not_a_measurement(have: Form | None, want: Form) -> None:
    """Refuse to construct across the measurement boundary, saying which way.

    `grade` already answers None here, so a caller that asked it first never
    arrives. This is for the one that did not: `build` would crop and resample
    a field into another field's shape and hand back plausible numbers, which
    is the failure the sample format exists to make impossible.
    """
    for form, side in ((have, "from"), (want, "into")):
        if form is not None and form.pix == "f32":
            raise ValueError(f"a measurement is not constructed {side}: "
                             f"{form.key()} is a field, not a picture")


def grade(have: Form, want: Form) -> str | None:
    """None if unreachable, EXACT if storable, APPROX if show-only."""
    if want.pix not in _FROM.get(have.pix, ()):
        return None
    hx, hy, hw, hh = have.rect
    wx, wy, ww, wh = want.rect
    if not (hx <= wx and hy <= wy and wx + ww <= hx + hw and wy + wh <= hy + hh):
        return None
    return EXACT if have.native else APPROX


#: One reformatter per thread — shared would race; per-call pays 49x setup.
_LOCAL = threading.local()


def _resample(out: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Resize via swscale — AREA down (bilinear aliases on downscale), BILINEAR up."""
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
    """Crop, resize, convert — order is definitional, not a caller's choice."""
    _not_a_measurement(None, want)
    x, y, w, h = want.rect
    out = frame[y:y + h, x:x + w]
    if (w, h) != want.out:
        out = _resample(out, want.out)
    if want.pix == "gray" and out.ndim == 3:
        out = _luma(out)
    elif want.pix == "bgr" and out.ndim == 2:
        raise ValueError("cannot invent chroma: gray cannot answer for bgr")
    return np.ascontiguousarray(out)
