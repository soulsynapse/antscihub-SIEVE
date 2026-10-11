"""EMA background model, emitting the absolute difference from it. v2's `background_ema`.

A stateful tool in a pull-style chain: the model at `row` depends on every
row before it. Recomputing from `row - warmup` on every request is correct
and slow, so this tool keeps its own checkpoints, keyed by the input's key
and alpha, and resumes from the nearest one. The second tool that does this
is where the pattern gets lifted into the player.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QSlider, QWidget

NAME = "background ema"
KIND = "frame"
DISPLAY = "image"
DEFAULTS = {"alpha": 0.02, "warmup": 150}

CHECKPOINT_EVERY = 16
_checkpoints: dict[tuple, dict[int, np.ndarray]] = {}


def run(frames, row, params):
    alpha = np.float32(params["alpha"])
    warmup = int(params["warmup"])
    states = _checkpoints.setdefault((frames.key, float(alpha)), {})
    if len(_checkpoints) > 8:
        _checkpoints.pop(next(iter(_checkpoints)))
    first = max(0, row - warmup)
    model = None
    for r in range(row - 1, first - 1, -1):
        if r in states:
            model = states[r].copy()
            first = r + 1
            break
    if model is None:
        model = np.asarray(frames(first), np.float32).copy()
        first += 1
    cur = model
    for r in range(first, row + 1):
        cur = np.asarray(frames(r), np.float32)
        model += alpha * (cur - model)
        if r % CHECKPOINT_EVERY == 0:
            states[r] = model.copy()
    return np.abs(cur - model)


class Settings(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.alpha = QSlider(Qt.Orientation.Horizontal)
        self.alpha.setRange(1, 500)
        self.alpha.setValue(int(DEFAULTS["alpha"] * 1000))
        self.warmup = QSlider(Qt.Orientation.Horizontal)
        self.warmup.setRange(10, 600)
        self.warmup.setValue(DEFAULTS["warmup"])
        self.readout = QLabel()
        form = QFormLayout(self)
        form.addRow("alpha", self.alpha)
        form.addRow("warmup frames", self.warmup)
        form.addRow("", self.readout)
        self.alpha.valueChanged.connect(self._emit)
        self.warmup.valueChanged.connect(self._emit)
        self._emit()

    def _emit(self):
        p = self.params()
        self.readout.setText(f"alpha {p['alpha']:.3f}   warmup {p['warmup']}")
        self.changed.emit()

    def params(self):
        return {"alpha": self.alpha.value() / 1000, "warmup": self.warmup.value()}


def settings(parent=None):
    return Settings(parent)
