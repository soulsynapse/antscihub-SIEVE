"""Per-block change energy from consecutive frames. v2's `block_signal`, change_energy only.

`it = g - gp`, `it*it` Gaussian-blurred at sigma 2 (the blur is the tensor's
spatial window), then block-mean reduced with partial edge blocks averaged
over their true pixels. Output is a small `(ny, nx)` float32 grid.
"""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QSlider, QWidget

NAME = "block signal"
KIND = "frame"
DISPLAY = "grid"
DEFAULTS = {"block": 16}

SIGMA = 2.0


def run(frames, row, params):
    block = int(params["block"])
    g = np.asarray(frames(row), np.float32)
    gp = np.asarray(frames(row - 1), np.float32) if row > 0 else g
    it = g - gp
    energy = cv2.GaussianBlur(it * it, (0, 0), SIGMA)
    ny, nx = -(-g.shape[0] // block), -(-g.shape[1] // block)
    padded = np.pad(energy, ((0, ny * block - g.shape[0]), (0, nx * block - g.shape[1])), constant_values=np.nan)
    cells = padded.reshape(ny, block, nx, block).transpose(0, 2, 1, 3).reshape(ny, nx, block * block)
    return np.nanmean(cells, axis=2).astype(np.float32)


class Settings(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.block = QSlider(Qt.Orientation.Horizontal)
        self.block.setRange(4, 64)
        self.block.setValue(DEFAULTS["block"])
        self.readout = QLabel()
        form = QFormLayout(self)
        form.addRow("block px", self.block)
        form.addRow("", self.readout)
        self.block.valueChanged.connect(self._emit)
        self._emit()

    def _emit(self):
        self.readout.setText(str(self.block.value()))
        self.changed.emit()

    def params(self):
        return {"block": self.block.value()}


def settings(parent=None):
    return Settings(parent)
