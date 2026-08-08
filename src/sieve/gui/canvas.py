"""The viewport: the frame the transport last handed over, drawn to fit.

Nothing here decides which frame is shown. It is handed one, it paints it, and
it holds it only so a resize has something to redraw — the playhead is
`transport/player.py`'s and the window is `timeline/bar.py`'s, and a copy of
either here would be the stale one.

Aspect ratio is preserved and the frame is never enlarged past its own pixels:
the decode side already hands back a proxy sized for display
(`transport/decode_worker.PROXY_WIDTH`), so upscaling here would invent detail
the user would then judge footage by.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

_BACKGROUND = QColor(18, 18, 22)
_HINT = QColor(120, 120, 130)
_EMPTY_HINT = "No frame"


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
