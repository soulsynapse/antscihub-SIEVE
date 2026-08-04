"""FFV1 in Matroska, written frame by frame from arrays.

The codec is not a preference. `docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md`
swept FFV1, lossless H.264 at three GOP settings, and a Zarr frame array against
the access pattern a tuning session actually has — sequential playback plus
scrubbing — and FFV1 took size, sequential decode, and correctness at once:
0.09 ms/frame sequential, 3.9 ms median seek, the smallest files, and
byte-identical back through the unchanged `VideoReader` in both gray and colour.
The pre-stated favourite, `-qp 0`, lost seek at default GOP and its *gray*
variant came back wrong on every frame — a lossless file serving pixels that
match no input frame. FFV1 is also intra-only by construction, so there is no
GOP setting here to get wrong.

**This module owns no identity.** It takes arrays and an fps and writes a file;
it does not know what a replicate is, what the crop was cut from, or how the
result will be keyed. `pipeline/materialize.py` owns all of that, and the split
is what lets the encoder be tested against a handful of synthetic frames with no
document in sight.

The pixel format follows the array's rank — a 2-D array is `gray`, a 3-D one is
BGR — because that is the only thing a writer can honestly infer. Colour goes
out as `bgr0` rather than through any YUV format: FFV1 is lossless either way,
but a YUV round trip would mean the file's *native* layout differs from the
array's and every read would pay a conversion whose exactness is a separate
claim. `bgr0` is the same three bytes with a pad byte.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any, Protocol, cast

import av
import numpy as np
from numpy.typing import NDArray

#: Rate denominators are capped here rather than passed through exactly.
#: Container frame rate is metadata — `Frame.index` is the authoritative
#: position everywhere in SIEVE — so what matters is that a player shows the
#: artifact at roughly the source's speed, not that 59.94 round-trips as
#: 60000/1001. An uncapped `Fraction(float)` is a 50-bit denominator, which some
#: muxers refuse outright.
MAX_RATE_DENOMINATOR = 10_000

#: The fallback when a container reports no frame rate. A file that says nothing
#: about its own speed still has to be written at *some* rate, and refusing over
#: metadata would throw away a decode nobody can get back cheaply.
FALLBACK_FPS = 30.0


class CropWriteError(RuntimeError):
    """The artifact could not be encoded: no frames, or a shape that changed."""


class _VideoStream(Protocol):
    """The encoding surface this module uses, named so strict typing can see it.

    PyAV ships type information, but `add_stream` is overloaded on a literal
    codec name (`ffv1` is not among the literals) and its packets are generic in
    a parameter the stubs leave open, so under `strict` every call through it
    resolves as partially unknown. Two honest responses exist — suppress the
    rule file-wide, or write down the surface actually used — and this is the
    second. It costs eight lines and it is checked: if a future PyAV renames
    `pix_fmt` or changes `encode`'s arity, the cast below stops matching and
    this file fails to type rather than failing at run time on the first
    artifact somebody writes.
    """

    width: int
    height: int
    pix_fmt: str

    def encode(self, frame: av.VideoFrame | None = None) -> Sequence[object]: ...


class _OutputContainer(Protocol):
    """The muxing surface, for `_VideoStream`'s reason."""

    def add_stream(self, codec_name: str, rate: Fraction) -> object: ...

    def mux(self, packets: object) -> None: ...


def write_ffv1(path: Path, frames: Iterable[NDArray[Any]], *, fps: float) -> int:
    """Encode `frames` to `path` as FFV1 in Matroska. Returns the frame count.

    The geometry and pixel format come from the first frame and are then fixed:
    a stream whose dimensions changed halfway would be a file no consumer could
    index by frame number, so a later frame that disagrees is refused rather
    than resized.

    Args:
        path: Where to write. Overwritten if it exists; its parent must exist.
        frames: Contiguous 8-bit arrays, `(h, w)` for gray or `(h, w, 3)` BGR.
            Consumed lazily — one frame is resident at a time, which is what
            lets a caller stream a whole clip through here.
        fps: Container frame rate. Metadata only; see `MAX_RATE_DENOMINATOR`.

    Raises:
        CropWriteError: if `frames` is empty, if a frame is not an 8-bit 2-D or
            3-channel array, or if one disagrees with the first frame's shape.
    """
    rate = Fraction(fps if fps > 0 else FALLBACK_FPS).limit_denominator(MAX_RATE_DENOMINATOR)
    written = 0
    with av.open(str(path), mode="w", format="matroska") as opened:
        container = cast(_OutputContainer, opened)
        stream: _VideoStream | None = None
        source_format = ""
        for array in frames:
            source_format = source_format or _source_format(array)
            if stream is None:
                stream = cast(_VideoStream, container.add_stream("ffv1", rate=rate))
                stream.width = int(array.shape[1])
                stream.height = int(array.shape[0])
                stream.pix_fmt = "gray" if source_format == "gray" else "bgr0"
            elif array.shape[:2] != (stream.height, stream.width):
                raise CropWriteError(
                    f"frame {written} is {array.shape[:2]}, but the stream was opened at "
                    f"{(stream.height, stream.width)} — a crop's geometry cannot change mid-file"
                )
            # `np.ascontiguousarray` rather than trusting the caller: a crop is
            # a *view* into a decoded frame, so its rows are strided, and PyAV
            # reads the buffer directly.
            frame = av.VideoFrame.from_ndarray(np.ascontiguousarray(array), format=source_format)
            for packet in stream.encode(frame):
                container.mux(packet)
            written += 1
        if stream is None:
            raise CropWriteError(f"nothing to encode: no frames were produced for {path}")
        for packet in stream.encode():
            container.mux(packet)
    return written


def _source_format(array: NDArray[Any]) -> str:
    """The PyAV format naming this array's own layout.

    Refuses rather than converts. A caller handing 16-bit or 4-channel data has
    a question about what the artifact should *be* that a writer cannot answer,
    and quietly narrowing it here is how a lossless path stops being lossless.
    """
    if array.dtype != np.uint8:
        raise CropWriteError(f"frames must be 8-bit, got {array.dtype}")
    if array.ndim == 2:
        return "gray"
    if array.ndim == 3 and array.shape[2] == 3:
        return "bgr24"
    raise CropWriteError(f"frames must be (h, w) or (h, w, 3), got shape {array.shape}")
