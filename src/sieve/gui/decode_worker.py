






















from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from sieve.core.pool_meter import PoolMeter
from sieve.core.types import ChannelSpec, VideoMetadata
from sieve.decode.reader import VideoDecodeError, VideoReader





PROXY_WIDTH = 1280


class DecodeWorker(QObject):


    opened = Signal(VideoMetadata)
    failed = Signal(str)
    frame_ready = Signal(int, QImage)

    def __init__(self, meter: PoolMeter | None = None) -> None:



        super().__init__()
        self._meter = PoolMeter() if meter is None else meter
        self._reader: VideoReader | None = None
        self._proxy_width = PROXY_WIDTH
        self._luma = False
        self._path: Path | None = None

    @Slot(int)
    def set_proxy_width(self, width: int) -> None:





        self._proxy_width = max(width, 1)

    @Slot(bool)
    def set_luma(self, enabled: bool) -> None:









        if enabled == self._luma:
            return
        self._luma = enabled
        if self._reader is None:
            return
        path = self._path
        self._reader.close()
        self._reader = None
        if path is None:
            return
        try:
            self._reader = VideoReader(path, luma=enabled)
        except VideoDecodeError as error:
            self.failed.emit(str(error))

    @Slot(str)
    def open(self, path: str) -> None:

        self.close()
        try:
            self._reader = VideoReader(Path(path), luma=self._luma)
        except VideoDecodeError as error:
            self.failed.emit(str(error))
            return
        self._path = Path(path)
        self.opened.emit(self._reader.metadata)

    @Slot(int)
    def request_frame(self, index: int) -> None:







        reader = self._reader
        if reader is None:
            return
        try:
            with self._meter.working():
                frame = reader.read(index, max_width=self._proxy_width)
        except VideoDecodeError as error:
            self.failed.emit(str(error))
            return

        data = frame.data
        if frame.channels is ChannelSpec.GRAY:
            image = QImage(
                data.tobytes(),
                frame.width,
                frame.height,
                frame.width,
                QImage.Format.Format_Grayscale8,
            )
        else:
            image = QImage(
                data.tobytes(),
                frame.width,
                frame.height,
                frame.width * 3,
                QImage.Format.Format_BGR888,
            )


        self.frame_ready.emit(index, image.copy())

    @Slot()
    def close(self) -> None:

        if self._reader is not None:
            self._reader.close()
            self._reader = None
        self._path = None
