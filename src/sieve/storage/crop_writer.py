




















from __future__ import annotations

from collections.abc import Iterable, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any, Protocol, cast

import av
import numpy as np
from numpy.typing import NDArray







MAX_RATE_DENOMINATOR = 10_000




FALLBACK_FPS = 30.0


class CropWriteError(RuntimeError):
    pass


class _VideoStream(Protocol):













    width: int
    height: int
    pix_fmt: str

    def encode(self, frame: av.VideoFrame | None = None) -> Sequence[object]: ...


class _OutputContainer(Protocol):


    def add_stream(self, codec_name: str, rate: Fraction) -> object: ...

    def mux(self, packets: object) -> None: ...


def write_ffv1(path: Path, frames: Iterable[NDArray[Any]], *, fps: float) -> int:


















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






    if array.dtype != np.uint8:
        raise CropWriteError(f"frames must be 8-bit, got {array.dtype}")
    if array.ndim == 2:
        return "gray"
    if array.ndim == 3 and array.shape[2] == 3:
        return "bgr24"
    raise CropWriteError(f"frames must be (h, w) or (h, w, 3), got shape {array.shape}")
