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

**A crop is drawn here and mapped by whoever knows what is on screen.** The
band is in this widget's coordinates, because that is the only frame of
reference a mouse event has; turning it into source pixels needs the form
currently displayed, which this deliberately does not know. Same split as
`forms.py` keeps — the rect's meaning belongs with whoever owns the form.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QRubberBand, QSizePolicy, QWidget

from sieve.gui.palette import PANEL

#: A drag shorter than this in either axis is a click that slipped.
_MIN_DRAG = 8


class FrameView(QWidget):
    """Blits one frame, letting the canvas decide how big it is."""

    #: x, y, w, h in this widget's coordinates. Only while `drawable`.
    drawn = Signal(int, int, int, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._frame: Any = None
        self._image: QImage | None = None
        self._pixmap: QPixmap | None = None
        self._band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._origin = None
        self.drawable = False

    def show_frame(self, frame: Any) -> None:
        """Take a contiguous uint8 array — HxWx3 BGR or HxW gray — and show it.

        Two formats and not one because gray is what the storage tiers hold: a
        window of whole colour frames is 47.6 MB apiece, and the crop the fill
        actually carries is a single plane.
        """
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
                QImage.Format.Format_BGR888
                if frame.ndim == 3
                else QImage.Format.Format_Grayscale8,
            )
        )
        self._rescale()
        self.repaint()

    # -- drawing a crop ----------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if not self.drawable:
            return
        self._origin = event.position().toPoint()
        self._band.setGeometry(QRect(self._origin, self._origin))
        self._band.show()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            self._band.setGeometry(
                QRect(self._origin, event.position().toPoint()).normalized()
            )

    def mouseReleaseEvent(self, event) -> None:
        del event
        if self._origin is None:
            return
        rect = self._band.geometry()
        self._band.hide()
        self._origin = None
        if rect.width() > _MIN_DRAG and rect.height() > _MIN_DRAG:
            self.drawn.emit(rect.x(), rect.y(), rect.width(), rect.height())

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
