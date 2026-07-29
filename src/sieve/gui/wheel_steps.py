from __future__ import annotations

from collections.abc import Callable
from time import monotonic

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QAbstractSlider,
    QAbstractSpinBox,
    QScrollBar,
    QWidget,
)


DETENT = 120


ACCEL_WINDOW_S = 0.25


ACCEL_EVERY = 4


ACCEL_MAX = 8


def _scrollable_ancestor(watched: QWidget, event: QWheelEvent) -> bool:
    delta = event.angleDelta()
    parent = watched.parentWidget()
    while parent is not None:
        if isinstance(parent, QAbstractScrollArea):
            bar = (
                parent.horizontalScrollBar()
                if abs(delta.x()) > abs(delta.y())
                else parent.verticalScrollBar()
            )
            if bar.maximum() > bar.minimum():
                return True
        if parent.isWindow():
            break
        parent = parent.parentWidget()
    return False


class WheelSteps(QObject):
    def __init__(
        self,
        parent: QObject | None = None,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        super().__init__(parent)
        self._clock = clock
        self._target: QObject | None = None
        self._last = float("-inf")
        self._run = 0
        self._residual = 0.0
        self._forwarding = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        kind = event.type()
        if kind is not QEvent.Type.Wheel and kind is not QEvent.Type.Polish:
            return super().eventFilter(watched, event)
        if not isinstance(watched, (QAbstractSlider, QAbstractSpinBox)):
            return super().eventFilter(watched, event)
        if isinstance(watched, QScrollBar):
            return super().eventFilter(watched, event)
        if kind is QEvent.Type.Polish:
            self._drop_wheel_focus(watched)
            return super().eventFilter(watched, event)
        if not isinstance(event, QWheelEvent):
            return super().eventFilter(watched, event)
        if not watched.hasFocus() and _scrollable_ancestor(watched, event):
            return self._pass_through(watched, event)
        now = self._clock()
        if watched is not self._target or now - self._last > ACCEL_WINDOW_S:
            self._run = 0
            self._residual = 0.0
        self._target = watched
        self._last = now
        self._residual += event.angleDelta().y()
        detents = int(self._residual / DETENT)
        self._residual -= detents * DETENT
        if detents != 0:
            multiplier = min(1 + self._run // ACCEL_EVERY, ACCEL_MAX)
            self._run += abs(detents)
            steps = detents * multiplier
            if isinstance(watched, QAbstractSlider):
                watched.setValue(watched.value() + steps * watched.singleStep())
            else:
                watched.stepBy(steps)
        return True

    @staticmethod
    def _drop_wheel_focus(watched: QWidget) -> None:
        if watched.focusPolicy() is Qt.FocusPolicy.WheelFocus:
            watched.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _pass_through(self, watched: QWidget, event: QWheelEvent) -> bool:
        if self._forwarding:
            return True
        self._forwarding = True
        try:
            target = watched.parentWidget()
            while target is not None:
                forwarded = QWheelEvent(
                    QPointF(watched.mapTo(target, event.position().toPoint())),
                    event.globalPosition(),
                    event.pixelDelta(),
                    event.angleDelta(),
                    event.buttons(),
                    event.modifiers(),
                    event.phase(),
                    event.inverted(),
                )
                forwarded.ignore()
                QCoreApplication.sendEvent(target, forwarded)
                if forwarded.isAccepted():
                    break
                if target.isWindow() or target.testAttribute(
                    Qt.WidgetAttribute.WA_NoMousePropagation
                ):
                    break
                target = target.parentWidget()
        finally:
            self._forwarding = False
        return True
