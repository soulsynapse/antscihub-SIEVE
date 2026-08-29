"""Section list with accent-edge selection; takes strings, reports an index."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, LINE, PANEL, PANEL_HOT, TEXT, rgb

# Public: segmented.py shares this mark width.
MARK_W = 3

_GUTTER = 4

_WIDTH = 150


def _sheet(selected: bool) -> str:
    edge = ACCENT if selected else PANEL
    return f"""
        #entry {{
            background: {rgb(PANEL)};
            border: 1px solid {rgb(LINE)};
            border-left: {MARK_W}px solid {rgb(edge)};
        }}
        #entry:hover {{ background: {rgb(PANEL_HOT)}; }}
        #label {{ color: {rgb(TEXT)}; font-size: {metrics.pt("name")}pt; }}
    """


class SectionNav(QWidget):
    """Every section of preferences, one entry each, one of them current."""

    chosen = Signal(int)

    def __init__(self, names: Sequence[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("nav")
        self.setFixedWidth(_WIDTH)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._current = -1
        self._entries: list[_Entry] = []

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(_GUTTER)
        for index, name in enumerate(names):
            entry = _Entry(name)
            entry.chosen.connect(lambda index=index: self.select(index))
            column.addWidget(entry)
            self._entries.append(entry)
        column.addStretch(1)

        self.select(0)

    def current(self) -> int:
        """The section being read, or -1 while there are none."""
        return self._current

    def select(self, index: int) -> None:
        """Open a section; out-of-range indices are silently ignored."""
        if not 0 <= index < len(self._entries) or index == self._current:
            return
        if 0 <= self._current < len(self._entries):
            self._entries[self._current].set_selected(False)
        self._current = index
        self._entries[index].set_selected(True)
        self.chosen.emit(index)

    def step(self, delta: int) -> None:
        """Move `delta` entries, clamped to bounds (no wrap)."""
        if not self._entries:
            return
        self.select(max(0, min(len(self._entries) - 1, self._current + delta)))

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.step(-1 if key == Qt.Key.Key_Up else +1)
            event.accept()
            return
        super().keyPressEvent(event)


class _Entry(QFrame):
    """One section on the surface. It reports being picked and marks nothing."""

    chosen = Signal()

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("entry")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._selected = False
        self.set_selected(False)
        palette.CHANGED.connect(self._restyle)
        metrics.CHANGED.connect(self._restyle)

        label = QLabel(name)
        label.setObjectName("label")

        column = QVBoxLayout(self)
        column.setContentsMargins(8, 6, 8, 6)
        column.setSpacing(0)
        column.addWidget(label)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._restyle()

    def _restyle(self) -> None:
        self.setStyleSheet(_sheet(self._selected))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.chosen.emit()
        super().mousePressEvent(event)
