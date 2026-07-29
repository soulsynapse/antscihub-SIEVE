from __future__ import annotations

from PySide6.QtWidgets import QSpinBox, QWidget


AUTO = 0


class BlockSpinBox(QSpinBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setKeyboardTracking(False)
        self.setToolTip("Block edge in working pixels; 0 is auto (64 source pixels).")

    def stepBy(self, steps: int) -> None:
        target = self.value() + steps
        if target <= AUTO and self.value() > 1:
            target = 1
        self.setValue(max(self.minimum(), min(self.maximum(), target)))
