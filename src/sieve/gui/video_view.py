from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

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
    QWheelEvent,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.zoom import MAX_ZOOM, MIN_ZOOM, ZOOM_STEP, Magnifier

__all__ = [
    "HANDLE_GRAB_PX",
    "HANDLE_PAINT_PX",
    "MAX_ZOOM",
    "MIN_DRAG_PX",
    "MIN_ZOOM",
    "NO_SELECTION",
    "ZOOM_STEP",
    "CropMode",
    "Handle",
    "VideoView",
]


MIN_DRAG_PX = 6


HANDLE_GRAB_PX = 7.0
HANDLE_PAINT_PX = 4.0

_BACKGROUND = QColor(24, 24, 27)
_LETTERBOX = QColor(16, 16, 18)
_HINT_TEXT = QColor(130, 130, 140)
_BOX = QColor(224, 224, 232)
_BOX_SELECTED = QColor(90, 170, 255)
_LABEL_BACKDROP = QColor(0, 0, 0, 170)
_DRAG = QColor(255, 255, 255)
_HANDLE_FILL = QColor(18, 18, 22)

NO_SELECTION = -1


class CropMode(StrEnum):
    DRAW = "draw"
    STAMP = "stamp"


class Handle(IntEnum):
    TOP_LEFT = 0
    TOP = 1
    TOP_RIGHT = 2
    LEFT = 3
    RIGHT = 4
    BOTTOM_LEFT = 5
    BOTTOM = 6
    BOTTOM_RIGHT = 7


_HANDLE_EDGES: dict[Handle, tuple[int, int]] = {
    Handle.TOP_LEFT: (-1, -1),
    Handle.TOP: (0, -1),
    Handle.TOP_RIGHT: (+1, -1),
    Handle.LEFT: (-1, 0),
    Handle.RIGHT: (+1, 0),
    Handle.BOTTOM_LEFT: (-1, +1),
    Handle.BOTTOM: (0, +1),
    Handle.BOTTOM_RIGHT: (+1, +1),
}

_HANDLE_CURSORS: dict[Handle, Qt.CursorShape] = {
    Handle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    Handle.TOP: Qt.CursorShape.SizeVerCursor,
    Handle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    Handle.LEFT: Qt.CursorShape.SizeHorCursor,
    Handle.RIGHT: Qt.CursorShape.SizeHorCursor,
    Handle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    Handle.BOTTOM: Qt.CursorShape.SizeVerCursor,
    Handle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
}


@dataclass(frozen=True, slots=True)
class _Adjustment:
    row: int

    handle: Handle | None
    roi: ROI
    origin: QPointF
    token: int

    @property
    def verb(self) -> str:
        return "Resize" if self.handle is not None else "Move"


class VideoView(QWidget):
    roi_drawn = Signal(ROI)

    selection_requested = Signal(int)

    roi_adjusted = Signal(int, ROI, int, str)

    roi_adjust_finished = Signal(int, int)

    stamp_size_changed = Signal(int, int)

    mode_changed = Signal(str)

    zoom_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(200)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAutoFillBackground(False)
        self.setMouseTracking(True)
        self._image: QImage | None = None
        self._source_size: tuple[int, int] | None = None
        self._replicates: list[Replicate] = []
        self._selected = NO_SELECTION
        self._drag_origin: QPoint | None = None
        self._drag_current: QPoint | None = None
        self._adjustment: _Adjustment | None = None
        self._gesture_serial = 0
        self._mode = CropMode.DRAW
        self._stamp_size: tuple[int, int] | None = None
        self._magnifier = Magnifier()
        self._hint = "File ▸ Open Video…   (Ctrl+O)"

    def set_source_size(self, size: tuple[int, int] | None) -> None:
        self._source_size = size
        if size is None:
            self._image = None
            self._replicates = []
            self._selected = NO_SELECTION
        self._cancel_gesture()
        self.reset_zoom()
        self.setCursor(
            Qt.CursorShape.CrossCursor
            if size is not None
            else Qt.CursorShape.ArrowCursor
        )
        self.update()

    def set_frame(self, image: QImage) -> None:
        self._image = image
        self.update()

    def set_replicates(self, replicates: list[Replicate]) -> None:
        self._replicates = replicates
        self._take_stamp_from_selection()
        self.update()

    def set_selected(self, index: int) -> None:
        if index == self._selected:
            return
        self._selected = index
        self._take_stamp_from_selection()
        self.update()

    def set_hint(self, text: str) -> None:
        self._hint = text
        self.update()

    @property
    def mode(self) -> CropMode:
        return self._mode

    def set_mode(self, mode: CropMode) -> None:
        if mode is self._mode:
            return
        self._mode = mode
        self.mode_changed.emit(mode)

    @property
    def stamp_size(self) -> tuple[int, int] | None:
        return self._stamp_size

    def set_stamp_size(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            return
        self._stamp_size = (width, height)

    def _take_stamp_from_selection(self) -> None:
        if not 0 <= self._selected < len(self._replicates):
            return
        roi = self._replicates[self._selected].roi
        if self._stamp_size == (roi.width, roi.height):
            return
        self._stamp_size = (roi.width, roi.height)
        self.stamp_size_changed.emit(roi.width, roi.height)

    @property
    def zoom(self) -> float:
        return self._magnifier.zoom

    def reset_zoom(self) -> None:
        if self._magnifier.reset():
            self.zoom_changed.emit(self._magnifier.zoom)
        self.update()

    def content_rect(self) -> QRectF:
        if self._source_size is None:
            return QRectF(self.rect())
        source_width, source_height = self._source_size
        if source_width <= 0 or source_height <= 0:
            return QRectF(self.rect())
        available = QRectF(self.rect())
        scale = min(
            available.width() / source_width, available.height() / source_height
        )
        width = source_width * scale
        height = source_height * scale
        return QRectF(
            available.x() + (available.width() - width) / 2.0,
            available.y() + (available.height() - height) / 2.0,
            width,
            height,
        )

    def view_rect(self) -> QRectF:
        fit = self.content_rect()
        if self._source_size is None:
            return fit
        return self._magnifier.view_rect(fit)

    def source_at(self, point: QPointF) -> QPointF:
        if self._source_size is None:
            return QPointF()
        source_width, source_height = self._source_size
        normalized = self._magnifier.at(point, self.content_rect())
        return QPointF(normalized.x() * source_width, normalized.y() * source_height)

    def to_source(self, point: QPointF) -> tuple[int, int]:
        if self._source_size is None:
            return (0, 0)
        source_width, source_height = self._source_size
        view = self.view_rect()
        if view.width() <= 0 or view.height() <= 0:
            return (0, 0)
        source = self.source_at(point)
        return (
            int(min(max(round(source.x()), 0), source_width)),
            int(min(max(round(source.y()), 0), source_height)),
        )

    def to_widget(self, roi: ROI) -> QRectF:
        if self._source_size is None:
            return QRectF()
        source_width, source_height = self._source_size
        view = self.view_rect()
        scale_x = view.width() / source_width
        scale_y = view.height() / source_height
        return QRectF(
            view.x() + roi.x * scale_x,
            view.y() + roi.y * scale_y,
            roi.width * scale_x,
            roi.height * scale_y,
        )

    def _placed(self, x: int, y: int, width: int, height: int) -> ROI:
        return ROI.placed_in(x, y, width, height, self._source_size)

    def _replicate_at(self, point: QPointF) -> int:
        for index in reversed(range(len(self._replicates))):
            if self.to_widget(self._replicates[index].roi).contains(point):
                return index
        return NO_SELECTION

    def _handle_rects(self) -> dict[Handle, QRectF]:
        if not 0 <= self._selected < len(self._replicates):
            return {}
        rect = self.to_widget(self._replicates[self._selected].roi)
        xs = (rect.left(), rect.center().x(), rect.right())
        ys = (rect.top(), rect.center().y(), rect.bottom())
        return {
            handle: QRectF(
                xs[horizontal + 1] - HANDLE_GRAB_PX,
                ys[vertical + 1] - HANDLE_GRAB_PX,
                HANDLE_GRAB_PX * 2.0,
                HANDLE_GRAB_PX * 2.0,
            )
            for handle, (horizontal, vertical) in _HANDLE_EDGES.items()
        }

    def _handle_at(self, point: QPointF) -> Handle | None:
        rects = self._handle_rects()
        corners = (
            Handle.TOP_LEFT,
            Handle.TOP_RIGHT,
            Handle.BOTTOM_LEFT,
            Handle.BOTTOM_RIGHT,
        )
        for handle in (*corners, *(h for h in Handle if h not in corners)):
            if handle in rects and rects[handle].contains(point):
                return handle
        return None

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._source_size is None:
            super().wheelEvent(event)
            return
        detents = event.angleDelta().y() / 120.0
        if detents == 0.0:
            super().wheelEvent(event)
            return
        if self._magnifier.wheel(detents, event.position(), self.content_rect()):
            self.zoom_changed.emit(self._magnifier.zoom)
            self.update()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._source_size is None:
            super().mousePressEvent(event)
            return
        point = event.position()
        self._drag_origin = point.toPoint()
        self._drag_current = self._drag_origin
        self._adjustment = None
        handle = self._handle_at(point)
        if handle is not None:
            self._begin_adjustment(handle, point)
        elif self._over_movable_selection(point):
            self._begin_adjustment(None, point)
        self.update()

    def _over_movable_selection(self, point: QPointF) -> bool:
        return 0 <= self._selected < len(self._replicates) and self.to_widget(
            self._replicates[self._selected].roi
        ).contains(point)

    def _begin_adjustment(self, handle: Handle | None, origin: QPointF) -> None:
        self._gesture_serial += 1
        self._adjustment = _Adjustment(
            row=self._selected,
            handle=handle,
            roi=self._replicates[self._selected].roi,
            origin=origin,
            token=self._gesture_serial,
        )

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is None:
            self._update_cursor(event.position())
            super().mouseMoveEvent(event)
            return
        point = event.position()
        self._drag_current = point.toPoint()
        if self._adjustment is not None and self._is_adjustment(
            QPointF(self._drag_origin), point
        ):
            self._emit_adjustment(self._adjustment, point)
        self.update()

    @staticmethod
    def _is_adjustment(origin: QPointF, end: QPointF) -> bool:
        return (
            abs(end.x() - origin.x()) >= MIN_DRAG_PX
            or abs(end.y() - origin.y()) >= MIN_DRAG_PX
        )

    def _update_cursor(self, point: QPointF) -> None:
        if self._source_size is None:
            return
        handle = self._handle_at(point)
        if handle is not None:
            self.setCursor(_HANDLE_CURSORS[handle])
        elif self._over_movable_selection(point):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def _emit_adjustment(self, adjustment: _Adjustment, point: QPointF) -> None:
        handle = adjustment.handle
        roi = (
            self._moved(adjustment, point)
            if handle is None
            else self._resized(adjustment, handle, point)
        )
        self.roi_adjusted.emit(adjustment.row, roi, adjustment.token, adjustment.verb)

    def _moved(self, adjustment: _Adjustment, point: QPointF) -> ROI:
        start = self.source_at(adjustment.origin)
        now = self.source_at(point)
        roi = adjustment.roi
        return self._placed(
            round(roi.x + now.x() - start.x()),
            round(roi.y + now.y() - start.y()),
            roi.width,
            roi.height,
        )

    def _resized(self, adjustment: _Adjustment, handle: Handle, point: QPointF) -> ROI:
        horizontal, vertical = _HANDLE_EDGES[handle]
        roi = adjustment.roi
        x, y = self.to_source(point)
        left = x if horizontal < 0 else roi.x
        right = x if horizontal > 0 else roi.right
        top = y if vertical < 0 else roi.y
        bottom = y if vertical > 0 else roi.bottom
        if left == right:
            right = left + 1
        if top == bottom:
            bottom = top + 1
        return ROI.from_corners(left, top, right, bottom).clamped_to(
            *self._source_size or (1, 1)
        )

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._drag_origin is None:
            super().mouseReleaseEvent(event)
            return
        origin, self._drag_origin = self._drag_origin, None
        adjustment, self._adjustment = self._adjustment, None
        end = event.position()
        self._drag_current = None
        self.update()
        start = QPointF(origin)
        if adjustment is not None:
            if self._is_adjustment(start, end):
                self._emit_adjustment(adjustment, end)
                self.roi_adjust_finished.emit(adjustment.row, adjustment.token)
            else:
                self.selection_requested.emit(adjustment.row)
            return
        if (
            abs(end.x() - start.x()) < MIN_DRAG_PX
            or abs(end.y() - start.y()) < MIN_DRAG_PX
        ):
            self._release_click(end)
            return
        x0, y0 = self.to_source(QPointF(origin))
        x1, y1 = self.to_source(end)
        roi = ROI.from_corners(x0, y0, x1, y1)
        if roi.width > 0 and roi.height > 0:
            self._stamp_size = (roi.width, roi.height)
            self.stamp_size_changed.emit(roi.width, roi.height)
            self.set_mode(CropMode.STAMP)
            self.roi_drawn.emit(roi)

    def _release_click(self, point: QPointF) -> None:
        row = self._replicate_at(point)
        if (
            row != NO_SELECTION
            or self._mode is not CropMode.STAMP
            or self._stamp_size is None
        ):
            self.selection_requested.emit(row)
            return
        width, height = self._stamp_size
        x, y = self.to_source(point)
        self.roi_drawn.emit(
            self._placed(x - width // 2, y - height // 2, width, height)
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self._drag_origin is not None:
            self._cancel_gesture()
            return
        super().keyPressEvent(event)

    def _cancel_gesture(self) -> None:
        adjustment, self._adjustment = self._adjustment, None
        self._drag_origin = None
        self._drag_current = None
        if adjustment is not None:
            self.roi_adjusted.emit(
                adjustment.row, adjustment.roi, adjustment.token, adjustment.verb
            )
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), _LETTERBOX)
        if self._image is None or self._source_size is None:
            self._paint_hint(painter)
            painter.end()
            return
        content = self.content_rect()
        painter.fillRect(content, _BACKGROUND)
        painter.setClipRect(content)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(self.view_rect(), self._image)
        self._paint_replicates(painter)
        self._paint_handles(painter)
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
            colour = QColor(_BOX_SELECTED if selected else _BOX)
            rect = self.to_widget(replicate.roi)
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

    def _paint_handles(self, painter: QPainter) -> None:
        painter.setPen(QPen(_BOX_SELECTED, 1.0))
        painter.setBrush(QBrush(_HANDLE_FILL))
        for rect in self._handle_rects().values():
            inset = HANDLE_GRAB_PX - HANDLE_PAINT_PX
            painter.drawRect(rect.adjusted(inset, inset, -inset, -inset))

    def _paint_drag(self, painter: QPainter) -> None:
        if (
            self._drag_origin is None
            or self._drag_current is None
            or self._adjustment is not None
        ):
            return
        pen = QPen(_DRAG, 1.0)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        box = QRectF(QPointF(self._drag_origin), QPointF(self._drag_current))
        painter.drawRect(box.normalized())
