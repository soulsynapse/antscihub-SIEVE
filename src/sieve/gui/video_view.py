"""Frame display with click-and-drag replicate boxes.

Coordinates convert straight from widget space to *source pixels*, never via
the proxy image the viewport happens to be showing. The proxy is a display
detail that can change resolution between frames; the ROI a user draws must
not. The precision limit is therefore the screen, which is the honest limit.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.core.replicates import Replicate
from sieve.core.types import ROI

#: A press-and-release shorter than this in both axes is a click, not a drag.
#: Below it there is no meaningful box, and treating it as one produces
#: one-pixel replicates every time a user misses a selection.
MIN_DRAG_PX = 6

_BACKGROUND = QColor(24, 24, 27)
_LETTERBOX = QColor(16, 16, 18)
_HINT_TEXT = QColor(130, 130, 140)
_BOX = QColor(224, 224, 232)
_BOX_SELECTED = QColor(90, 170, 255)
_LABEL_BACKDROP = QColor(0, 0, 0, 170)
_DRAG = QColor(255, 255, 255)

NO_SELECTION = -1


class VideoView(QWidget):
    """Letterboxed frame viewport that draws and reports replicate regions."""

    #: A drag completed, in source-pixel coordinates.
    roi_drawn = Signal(ROI)
    #: A click selected a replicate row, or `NO_SELECTION` for empty space.
    selection_requested = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(200)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(False)

        self._image: QImage | None = None
        self._source_size: tuple[int, int] | None = None
        self._replicates: list[Replicate] = []
        self._selected = NO_SELECTION
        self._drag_origin: QPoint | None = None
        self._drag_current: QPoint | None = None
        self._hint = "File ▸ Open Video…   (Ctrl+O)"

    # ---- content ---------------------------------------------------------

    def set_source_size(self, size: tuple[int, int] | None) -> None:
        """Set the source dimensions ROIs are expressed in, or None to clear."""
        self._source_size = size
        if size is None:
            self._image = None
            self._replicates = []
            self._selected = NO_SELECTION
        self.setCursor(
            Qt.CursorShape.CrossCursor if size is not None else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def set_frame(self, image: QImage) -> None:
        """Display a decoded frame."""
        self._image = image
        self.update()

    def set_replicates(self, replicates: list[Replicate]) -> None:
        """Replace the overlay boxes."""
        self._replicates = replicates
        self.update()

    def set_selected(self, index: int) -> None:
        """Highlight one replicate, or `NO_SELECTION` for none."""
        if index == self._selected:
            return
        self._selected = index
        self.update()

    def set_hint(self, text: str) -> None:
        """Message shown when no frame is loaded."""
        self._hint = text
        self.update()

    # ---- geometry --------------------------------------------------------

    def _content_rect(self) -> QRectF:
        """Aspect-fit rectangle the source occupies inside this widget."""
        if self._source_size is None:
            return QRectF(self.rect())
        source_width, source_height = self._source_size
        if source_width <= 0 or source_height <= 0:
            return QRectF(self.rect())

        available = QRectF(self.rect())
        scale = min(available.width() / source_width, available.height() / source_height)
        width = source_width * scale
        height = source_height * scale
        return QRectF(
            available.x() + (available.width() - width) / 2.0,
            available.y() + (available.height() - height) / 2.0,
            width,
            height,
        )

    def _to_source(self, point: QPointF) -> tuple[int, int]:
        """Widget point to source pixel, clamped inside the frame."""
        if self._source_size is None:
            return (0, 0)
        source_width, source_height = self._source_size
        content = self._content_rect()
        if content.width() <= 0 or content.height() <= 0:
            return (0, 0)
        x = (point.x() - content.x()) / content.width() * source_width
        y = (point.y() - content.y()) / content.height() * source_height
        return (
            int(min(max(round(x), 0), source_width)),
            int(min(max(round(y), 0), source_height)),
        )

    def _to_widget(self, roi: ROI) -> QRectF:
        """Source-pixel ROI to widget rectangle."""
        if self._source_size is None:
            return QRectF()
        source_width, source_height = self._source_size
        content = self._content_rect()
        scale_x = content.width() / source_width
        scale_y = content.height() / source_height
        return QRectF(
            content.x() + roi.x * scale_x,
            content.y() + roi.y * scale_y,
            roi.width * scale_x,
            roi.height * scale_y,
        )

    def _replicate_at(self, point: QPointF) -> int:
        """Topmost replicate containing `point`, or `NO_SELECTION`."""
        for index in reversed(range(len(self._replicates))):
            if self._to_widget(self._replicates[index].roi).contains(point):
                return index
        return NO_SELECTION

    # ---- input -----------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Begin a box drag."""
        if event.button() != Qt.MouseButton.LeftButton or self._source_size is None:
            super().mousePressEvent(event)
            return
        self._drag_origin = event.position().toPoint()
        self._drag_current = self._drag_origin
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Extend the in-progress box."""
        if self._drag_origin is None:
            super().mouseMoveEvent(event)
            return
        self._drag_current = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish a drag as a new ROI, or a click as a selection."""
        if event.button() != Qt.MouseButton.LeftButton or self._drag_origin is None:
            super().mouseReleaseEvent(event)
            return

        origin, self._drag_origin = self._drag_origin, None
        end = event.position().toPoint()
        self._drag_current = None
        self.update()

        travelled_x = abs(end.x() - origin.x())
        travelled_y = abs(end.y() - origin.y())
        if travelled_x < MIN_DRAG_PX or travelled_y < MIN_DRAG_PX:
            self.selection_requested.emit(self._replicate_at(QPointF(end)))
            return

        x0, y0 = self._to_source(QPointF(origin))
        x1, y1 = self._to_source(QPointF(end))
        roi = ROI.from_corners(x0, y0, x1, y1)
        if roi.width > 0 and roi.height > 0:
            self.roi_drawn.emit(roi)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Escape abandons an in-progress drag."""
        if event.key() == Qt.Key.Key_Escape and self._drag_origin is not None:
            self._drag_origin = None
            self._drag_current = None
            self.update()
            return
        super().keyPressEvent(event)

    # ---- painting --------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the frame, then the replicate overlay."""
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _LETTERBOX)

        if self._image is None or self._source_size is None:
            self._paint_hint(painter)
            painter.end()
            return

        content = self._content_rect()
        painter.fillRect(content, _BACKGROUND)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(content, self._image)

        self._paint_replicates(painter)
        self._paint_drag(painter)
        painter.end()

    def _paint_hint(self, painter: QPainter) -> None:
        painter.setPen(QPen(_HINT_TEXT))
        font = QFont(painter.font())
        font.setPointSizeF(font.pointSizeF() + 1.0)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._hint)

    def _paint_replicates(self, painter: QPainter) -> None:
        label_font = QFont(painter.font())
        label_font.setPointSizeF(max(label_font.pointSizeF() - 0.5, 6.0))
        painter.setFont(label_font)
        metrics = painter.fontMetrics()

        for index, replicate in enumerate(self._replicates):
            selected = index == self._selected
            colour = _BOX_SELECTED if selected else _BOX
            rect = self._to_widget(replicate.roi)

            painter.setPen(QPen(colour, 2.0 if selected else 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            label = replicate.name
            text_width = metrics.horizontalAdvance(label)
            backdrop = QRectF(
                rect.x(),
                max(rect.y() - metrics.height() - 2.0, 0.0),
                text_width + 8.0,
                metrics.height() + 2.0,
            )
            painter.fillRect(backdrop, QBrush(_LABEL_BACKDROP))
            painter.setPen(QPen(colour))
            painter.drawText(
                backdrop.adjusted(4.0, 0.0, 0.0, 0.0),
                Qt.AlignmentFlag.AlignVCenter,
                label,
            )

    def _paint_drag(self, painter: QPainter) -> None:
        if self._drag_origin is None or self._drag_current is None:
            return
        pen = QPen(_DRAG, 1.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        box = QRectF(QPointF(self._drag_origin), QPointF(self._drag_current))
        painter.drawRect(box.normalized())
