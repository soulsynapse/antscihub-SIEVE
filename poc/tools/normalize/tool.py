"""Per-frame contrast normalization to mean 128, sd 32. v2's `normalize`."""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFormLayout, QWidget

NAME = "normalize"
KIND = "frame"
DISPLAY = "image"
DEFAULTS = {"on": True}

TARGET_MEAN = 128.0
TARGET_SD = 32.0
MIN_STD = 1e-3


def run(frames, row, params):
    g = frames(row)
    if not params["on"]:
        return g
    data = np.asarray(g, np.float32)
    mean, std = cv2.meanStdDev(data)
    mean, std = float(mean[0, 0]), float(std[0, 0])
    if std < MIN_STD:
        return data - np.float32(mean)
    a = TARGET_SD / std
    out = np.multiply(data, np.float32(a), dtype=np.float32)
    np.add(out, np.float32(TARGET_MEAN - mean * a), out=out)
    return out


class Settings(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.on = QCheckBox("z-score to mean 128, sd 32")
        self.on.setChecked(DEFAULTS["on"])
        QFormLayout(self).addRow(self.on)
        self.on.toggled.connect(self.changed)

    def params(self):
        return {"on": self.on.isChecked()}


def settings(parent=None):
    return Settings(parent)
