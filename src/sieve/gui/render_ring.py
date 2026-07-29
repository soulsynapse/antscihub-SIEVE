











































from __future__ import annotations

from threading import Lock

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from sieve.bench.retention_trace import (
    PUT,
    TRACE,
    UNKNOWN_PLAYHEAD,
    AccessEvent,
    TraceRecorder,
)
from sieve.core.shares import RENDER_RING_SHARE, resolved_bytes
from sieve.core.types import ChannelSpec, Frame
from sieve.gui.decode_worker import PROXY_WIDTH
from sieve.gui.proxy_cache import ProxyFrameCache


class RenderFrameRing:


    def __init__(
        self, capacity_bytes: int | None = None, *, trace: TraceRecorder | None = None
    ) -> None:
        self._lock = Lock()



        self._trace = TRACE if trace is None else trace
        self._frames = ProxyFrameCache(
            capacity_bytes=resolved_bytes(RENDER_RING_SHARE)
            if capacity_bytes is None
            else capacity_bytes
        )



        self._proxy_width = PROXY_WIDTH
        self._frontier: int | None = None

    @property
    def frontier(self) -> int | None:

        with self._lock:
            return self._frontier

    def set_proxy_width(self, width: int) -> None:

        with self._lock:
            if width == self._proxy_width:
                return
            self._proxy_width = max(width, 1)
            self._frames.clear()

    def begin(self) -> None:






        with self._lock:
            self._frontier = None

    def put(self, frame: Frame) -> None:






        if frame.channels is not ChannelSpec.GRAY or frame.data.dtype != np.uint8:
            return
        data = np.ascontiguousarray(frame.data)
        height, width = data.shape[:2]
        image = QImage(data.tobytes(), width, height, width, QImage.Format.Format_Grayscale8)
        with self._lock:
            if 0 < self._proxy_width < width:
                image = image.scaledToWidth(
                    self._proxy_width, Qt.TransformationMode.SmoothTransformation
                )
            else:



                image = image.copy()
            self._frames.put(frame.index, image)
            self._frontier = frame.index
        if self._trace.enabled:
            self._trace.record(
                AccessEvent(
                    op=PUT,
                    index=frame.index,
                    playhead=UNKNOWN_PLAYHEAD,
                    kind="",
                    source="",
                    frontier=frame.index,
                )
            )

    def get(self, index: int) -> QImage | None:

        with self._lock:
            return self._frames.get(index)

    def clear(self) -> None:

        with self._lock:
            self._frames.clear()
            self._frontier = None
