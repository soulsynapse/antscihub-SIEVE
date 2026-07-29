








from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QWidget


DETENT = 120


def _event(kind: QEvent.Type, point: QPointF, *, held: bool) -> QMouseEvent:
    return QMouseEvent(
        kind,
        point,
        point,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton if held else Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )


def press(widget: QWidget, point: QPointF) -> None:

    widget.mousePressEvent(_event(QEvent.Type.MouseButtonPress, point, held=True))


def move(widget: QWidget, point: QPointF) -> None:

    widget.mouseMoveEvent(_event(QEvent.Type.MouseMove, point, held=True))


def release(widget: QWidget, point: QPointF) -> None:

    widget.mouseReleaseEvent(_event(QEvent.Type.MouseButtonRelease, point, held=False))


def drag(widget: QWidget, start: QPointF, end: QPointF) -> None:

    press(widget, start)
    move(widget, end)
    release(widget, end)


def click(widget: QWidget, point: QPointF) -> None:

    drag(widget, point, point)


def leave(widget: QWidget) -> None:

    widget.leaveEvent(QEvent(QEvent.Type.Leave))


def wheel(widget: QWidget, point: QPointF, detents: int) -> None:

    widget.wheelEvent(
        QWheelEvent(
            point,
            point,
            QPoint(0, 0),
            QPoint(0, detents * DETENT),
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
    )
