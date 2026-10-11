"""Reduce resolution by a linear scale factor. v2's `rescale`, as a tool."""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QSlider, QWidget
from PySide6.QtCore import Qt

NAME = "rescale"
KIND = "frame"
DISPLAY = "image"
DEFAULTS = {"scale": 0.5}


def run(frames, row, params):
    g = frames(row)
    s = float(params["scale"])
    if s >= 1.0:
        return g
    w = max(8, round(g.shape[1] * s))
    h = max(8, round(g.shape[0] * s))
    return cv2.resize(g, (w, h), interpolation=cv2.INTER_AREA)


class Settings(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale = QSlider(Qt.Orientation.Horizontal)
        self.scale.setRange(10, 100)
        self.scale.setValue(int(DEFAULTS["scale"] * 100))
        self.readout = QLabel()
        form = QFormLayout(self)
        form.addRow("scale", self.scale)
        form.addRow("", self.readout)
        self.scale.valueChanged.connect(self._emit)
        self._emit()

    def _emit(self):
        self.readout.setText(f"{self.scale.value() / 100:.2f}")
        self.changed.emit()

    def params(self):
        return {"scale": self.scale.value() / 100}


def settings(parent=None):
    return Settings(parent)
