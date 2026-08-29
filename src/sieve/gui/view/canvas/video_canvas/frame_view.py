"""One decoded frame on the stage, scaled to whatever room the canvas gave it.

Every rule here is a measured one from
`docs/findings/2026.08.22-what-froze-the-felt-loop.md`, where every freeze in
the tuning loop traced to the presentation layer and none to the tier stack.
They are cheap to honour and expensive to rediscover, so they are written
down beside the code that has to keep them.

**Nothing that updates participates in layout negotiation.** The size policy
is Ignored and no size hint is offered: a widget whose hint follows its
content re-negotiates the splitter every time the content changes, and the
session that found this was resizing its video every few seconds because a
*text label* was nudging the splitter. The canvas hands down geometry; this
scales into it.

**Painting is synchronous.** `repaint()` and not `update()`, because during a
drag the app never returns to the event loop — each `processEvents` pulls the
next mouse move — so a deferred paint starves. That was measured at 198
serves and zero paints across a three-second drag storm, and it is why the
earlier probe, which counted `setPixmap` calls, said the loop was fine while
the picture sat still.

**Scaled once per change, not once per paint.** The pixmap is rebuilt when
the frame changes or the geometry does, and `paintEvent` blits what is
already the right size. `FastTransformation` because this is a live surface;
the smooth one belongs to whatever renders a report, which
`experiments/tool-experiments/surfaces.py` keeps as different code for the
same reason.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.gui.palette import PANEL


class FrameView(QWidget):
    """Blits one BGR frame, letting the canvas decide how big it is."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._frame: Any = None
        self._image: QImage | None = None
        self._pixmap: QPixmap | None = None

    def show_frame(self, frame: Any) -> None:
        """Take a contiguous HxWx3 uint8 BGR array and put it on screen now."""
        self._frame = frame
        # The QImage is a view over the array's buffer, so the array has to
        # outlive it — holding both is the point, not redundancy.
        self._image = (
            None
            if frame is None
            else QImage(
                frame.data,
                frame.shape[1],
                frame.shape[0],
                frame.strides[0],
                QImage.Format.Format_BGR888,
            )
        )
        self._rescale()
        self.repaint()

    def _rescale(self) -> None:
        if self._image is None or self.width() <= 0 or self.height() <= 0:
            self._pixmap = None
            return
        self._pixmap = QPixmap.fromImage(self._image).scaled(
            self.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        if self._pixmap is None:
            painter.fillRect(self.rect(), PANEL)
        else:
            painter.drawPixmap(0, 0, self._pixmap)
        painter.end()
