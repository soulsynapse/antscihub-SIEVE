from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QWheelEvent
from PySide6.QtWidgets import QComboBox, QWidget


NAVIGATION_KEYS = frozenset(
    {
        Qt.Key.Key_Up,
        Qt.Key.Key_Down,
        Qt.Key.Key_PageUp,
        Qt.Key.Key_PageDown,
        Qt.Key.Key_Home,
        Qt.Key.Key_End,
    }
)


class CommitCombo(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if self.focusPolicy() is Qt.FocusPolicy.WheelFocus:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() in NAVIGATION_KEYS and not self.view().isVisible():
            self.showPopup()
            e.accept()
            return
        super().keyPressEvent(e)

    def wheelEvent(self, e: QWheelEvent) -> None:
        e.ignore()
