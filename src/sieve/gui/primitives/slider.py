"""Horizontal slider that lets the wheel past it.

The wheel is refused because a `QSlider` takes it without focus: scrolling a
settings column would silently edit every slider passed on the way down.
Horizontal only — every sub-control rule below is written `:horizontal`, so a
vertical one would come out undressed rather than visibly wrong.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QSlider, QWidget

from sieve.gui import palette
from sieve.gui.palette import ACCENT, LINE, TEXT, rgb

_GROOVE = 3
_HANDLE = 12


class Slider(QSlider):
    """Horizontal slider in the tree's palette roles; ignores the wheel."""

    def __init__(self, low: int = 0, high: int = 100, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setObjectName("slider")
        self.setRange(low, high)
        self.setSingleStep(1)
        self.setPageStep(1)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._dress()
        # Bound method so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._dress)

    def show_value(self, value: int) -> None:
        """Move the handle without emitting valueChanged."""
        self.blockSignals(True)
        self.setValue(value)
        self.blockSignals(False)

    def wheelEvent(self, event) -> None:
        event.ignore()

    def _dress(self) -> None:
        self.setStyleSheet(f"""
            #slider::groove:horizontal {{
                background: {rgb(LINE)};
                height: {_GROOVE}px;
                border-radius: {_GROOVE // 2}px;
            }}
            #slider::sub-page:horizontal {{
                background: {rgb(ACCENT)};
                height: {_GROOVE}px;
                border-radius: {_GROOVE // 2}px;
            }}
            #slider::handle:horizontal {{
                background: {rgb(ACCENT)};
                width: {_HANDLE}px;
                border-radius: {_HANDLE // 2}px;
                margin: -{(_HANDLE - _GROOVE) // 2}px 0;
            }}
            #slider::handle:horizontal:hover {{ background: {rgb(TEXT)}; }}
            #slider::handle:horizontal:focus {{ background: {rgb(TEXT)}; }}
            #slider::sub-page:horizontal:disabled {{ background: {rgb(LINE)}; }}
            #slider::handle:horizontal:disabled {{ background: {rgb(LINE)}; }}
        """)
