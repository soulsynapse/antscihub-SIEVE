
















































from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any, Self

import cv2
from numpy.typing import NDArray

from sieve.core.types import ChannelSpec, Frame, VideoMetadata



GRAB_FORWARD_LIMIT = 40


class VideoDecodeError(RuntimeError):
    pass


class VideoReader:






    def __init__(self, path: Path | str, *, luma: bool = False) -> None:









        self._path = Path(path)
        if not self._path.is_file():
            raise VideoDecodeError(f"No such video file: {self._path}")

        self._capture = cv2.VideoCapture(str(self._path))
        if not self._capture.isOpened():
            raise VideoDecodeError(f"Could not open video: {self._path}")

        self._luma = luma
        if luma:



            self._capture.set(cv2.CAP_PROP_CONVERT_RGB, 0)

        self._metadata = self._read_metadata()
        if self._metadata.frame_count <= 0:
            self._capture.release()
            raise VideoDecodeError(f"Video reports no frames: {self._path}")


        self._cursor = 0

    def _read_metadata(self) -> VideoMetadata:
        return VideoMetadata(
            path=self._path,
            width=int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=float(self._capture.get(cv2.CAP_PROP_FPS)),
            frame_count=int(self._capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        )

    @property
    def metadata(self) -> VideoMetadata:

        return self._metadata

    @property
    def is_open(self) -> bool:

        return self._capture.isOpened()

    @property
    def luma(self) -> bool:






        return self._luma

    def read(self, index: int, max_width: int | None = None) -> Frame:

















        if not 0 <= index < self._metadata.frame_count:
            raise VideoDecodeError(
                f"Frame {index} out of range 0..{self._metadata.frame_count - 1}"
            )

        self._position_at(index)


        ok, data = self._capture.read()
        if not ok:
            self._cursor = -1
            raise VideoDecodeError(f"Failed to decode frame {index} of {self._path}")
        self._cursor = index + 1

        if self._luma:
            self._check_luma_plane(data, index)

        return Frame(
            data=_downscale(data, max_width),
            index=index,
            channels=ChannelSpec.GRAY if self._luma else ChannelSpec.BGR,
        )

    def _check_luma_plane(self, data: NDArray[Any], index: int) -> None:
















        expected = (self._metadata.height, self._metadata.width)
        if data.ndim != 2 or data.shape != expected:
            raise VideoDecodeError(
                f"Frame {index} of {self._path}: asked for the luma plane and got an array "
                f"of shape {data.shape}, not {expected}. This build's decoder does not hand "
                f"back planar luma for this source; open the reader without luma=True."
            )

    def _position_at(self, index: int) -> None:

        delta = index - self._cursor
        if delta == 0:
            return
        if 0 < delta <= GRAB_FORWARD_LIMIT:
            for _ in range(delta):
                if not self._capture.grab():
                    break
            return
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, index)

    def close(self) -> None:

        self._capture.release()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def _downscale(data: NDArray[Any], max_width: int | None) -> NDArray[Any]:

    source_height, source_width = data.shape[:2]
    if max_width is None or source_width <= max_width:
        return data
    scale = max_width / source_width
    target = (max_width, max(round(source_height * scale), 1))
    return cv2.resize(data, target, interpolation=cv2.INTER_AREA)
