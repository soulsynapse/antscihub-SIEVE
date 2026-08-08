"""The viewport: the frame it was last handed, drawn to fit.

Nothing here decides which frame is shown. It is handed one, it paints it, and
it holds it only so a resize has something to redraw — the playhead is
`transport/player.py`'s, the window is `timeline/bar.py`'s, and *which* of the
two frames a source index now has is `app.py`'s, since only the window knows
where the walk is standing. A copy of any of the three here would be the stale
one.

Aspect ratio is preserved and the frame is never enlarged past its own pixels:
the decode side already hands back a proxy sized for display
(`transport/decode_worker.PROXY_WIDTH`), so upscaling here would invent detail
the user would then judge footage by.

**A node's output has no display range, so the greyscale is stretched between
that frame's own extremes.** `graph_panel.value_range`'s question one surface
over, and answered differently on purpose: a trace is read against an axis and
so wants a floor that does not move, while a picture has no axis and a frame
mapped through a fixed range is black on every tool whose units are not
already 0..1. What it costs is that brightness is not comparable across frames,
which is why nothing here is offered as a measurement.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

_BACKGROUND = QColor(18, 18, 22)
_HINT = QColor(120, 120, 130)
_EMPTY_HINT = "No frame"


def image_of(values: NDArray[np.float32]) -> QImage | None:
    """`values` as a greyscale image, or `None` if there is no picture in them.

    `None` for anything that is not a two-dimensional array with a finite value
    in it: a caller showing a node's output cannot know in advance that the node
    has one, and an image invented for a frame that has none would be a viewport
    asserting something about the graph.

    The buffer is copied because `QImage` does not own the one it is
    constructed over, and the array it would otherwise point into is local.
    """
    array = np.asarray(values, np.float32)
    if array.ndim != 2 or array.size == 0:
        return None
    finite = array[np.isfinite(array)]
    if finite.size == 0:
        return None
    low, high = float(finite.min()), float(finite.max())
    spread = high - low
    # A constant frame is flat rather than saturated: dividing by the spread
    # would be a division by zero, and either extreme of the ramp would be a
    # brightness the frame did not earn.
    scaled = np.zeros_like(array) if spread <= 0.0 else (array - low) / spread
    # Every finite value is already inside 0..1 by construction — `low` and
    # `high` are this frame's own — so the only thing left to place is the
    # non-finite one, which `image_of`'s caller has no better answer for either.
    grey = np.ascontiguousarray(
        np.nan_to_num(scaled, nan=0.0, posinf=1.0, neginf=0.0) * 255.0
    ).astype(np.uint8)
    height, width = grey.shape
    return QImage(grey.data, width, height, width, QImage.Format.Format_Grayscale8).copy()


class VideoCanvas(QWidget):
    """Draws the most recent frame, centred, letterboxed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frame: QImage | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @property
    def frame(self) -> QImage | None:
        """The image on screen, or None before the first frame arrives."""
        return self._frame

    def set_frame(self, index: int, image: QImage) -> None:
        """Show `image`. `index` is accepted and ignored — the readout is the bar's."""
        del index
        self._frame = image
        self.update()

    def set_values(self, index: int, values: NDArray[np.float32]) -> bool:
        """Show `values` as a frame. False, and nothing shown, if they are no picture.

        The refusal is returned rather than raised because the caller has a
        second frame in hand for exactly this case — the source — and a node
        whose output is not an image is an ordinary place for the walk to stand,
        not an error.
        """
        image = image_of(values)
        if image is None:
            return False
        self.set_frame(index, image)
        return True

    def clear(self) -> None:
        """Return to the empty state. The source has gone."""
        self._frame = None
        self.update()

    def frame_rect(self) -> QRectF:
        """Where the frame is painted, empty when there is none.

        Exposed for the same reason the strip exposes its rects: a painted pixel
        is not something a test can ask about, and "the footage is not stretched"
        is a claim about this rectangle.
        """
        image = self._frame
        if image is None or image.isNull():
            return QRectF()
        scale = min(self.width() / image.width(), self.height() / image.height(), 1.0)
        width = image.width() * scale
        height = image.height() * scale
        return QRectF((self.width() - width) / 2.0, (self.height() - height) / 2.0, width, height)

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _BACKGROUND)
        box = self.frame_rect()
        if box.isEmpty() or self._frame is None:
            painter.setPen(_HINT)
            painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignCenter), _EMPTY_HINT)
            painter.end()
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(box, self._frame)
        painter.end()
