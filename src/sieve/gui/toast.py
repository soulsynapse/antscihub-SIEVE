from __future__ import annotations

from contextlib import suppress

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QLabel,
    QVBoxLayout,
    QWidget,
)


DEFAULT_TIMEOUT_MS = 8000

FADE_MS = 180


MARGIN = 18


MAX_WIDTH = 380

_STYLE = """
QFrame#toastPanel {
    background-color: rgba(32, 33, 36, 235);
    border: 1px solid rgba(255, 255, 255, 38);
    border-radius: 8px;
}
QLabel#toastText {
    color: rgba(255, 255, 255, 229);
    font-size: 12px;
    background: transparent;
}
"""


class Toast(QFrame):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toastPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_STYLE)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to dismiss")
        self._label = QLabel(self)
        self._label.setObjectName("toastText")
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._label.setMaximumWidth(MAX_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 11)
        layout.addWidget(self._label)
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._fade = QPropertyAnimation(self._opacity, b"opacity", self)
        self._fade.setDuration(FADE_MS)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)
        parent.installEventFilter(self)
        self.hide()

    def show_message(self, text: str, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> None:
        self._label.setText(text)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self._animate_to(1.0)
        self._dismiss_timer.start(timeout_ms)

    @property
    def message(self) -> str:
        return self._label.text()

    def dismiss(self) -> None:
        self._dismiss_timer.stop()
        if not self.isVisible():
            return
        self._animate_to(0.0, then_hide=True)

    def _animate_to(self, opacity: float, *, then_hide: bool = False) -> None:
        self._fade.stop()
        with suppress(RuntimeError):
            self._fade.finished.disconnect()
        if then_hide:
            self._fade.finished.connect(self.hide)
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(opacity)
        self._fade.start()

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.move(
            max(MARGIN, parent.width() - self.width() - MARGIN),
            max(MARGIN, parent.height() - self.height() - MARGIN),
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.parentWidget() and event.type() == QEvent.Type.Resize:
            self._reposition()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        del event
        self.dismiss()
