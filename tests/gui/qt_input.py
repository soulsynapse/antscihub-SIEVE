"""Synthetic mouse input for widget tests.

Events are constructed and handed to the widget's handlers directly rather than
posted through `QTest.mouseMove`, which needs a real window under a real cursor
and is unreliable on the offscreen platform CI runs. The widget code under test
reads only `button()`, `buttons()`, and `position()`, all of which are set here
exactly as Qt would.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QWidget

#: One wheel detent, in eighths of a degree — Qt's unit for `angleDelta`.
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
    """Left-button press at `point` in widget coordinates."""
    widget.mousePressEvent(_event(QEvent.Type.MouseButtonPress, point, held=True))


def move(widget: QWidget, point: QPointF) -> None:
    """Left-button drag to `point` in widget coordinates."""
    widget.mouseMoveEvent(_event(QEvent.Type.MouseMove, point, held=True))


def release(widget: QWidget, point: QPointF) -> None:
    """Left-button release at `point` in widget coordinates."""
    widget.mouseReleaseEvent(_event(QEvent.Type.MouseButtonRelease, point, held=False))


def drag(widget: QWidget, start: QPointF, end: QPointF) -> None:
    """Press, move, and release — the full gesture."""
    press(widget, start)
    move(widget, end)
    release(widget, end)


def click(widget: QWidget, point: QPointF) -> None:
    """Press and release without travelling."""
    drag(widget, point, point)


def wheel(widget: QWidget, point: QPointF, detents: int) -> None:
    """Scroll `detents` notches at `point`; positive is towards the user's screen."""
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
