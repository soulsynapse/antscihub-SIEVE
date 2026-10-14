"""Series tool: mean |frame-to-frame difference| over the loop window, gated by a threshold."""
import cv2
import numpy as np

NAME, KIND, EXPECTS = "motion", "series", "gray"
DEFAULTS = {"gate": 2.0}

_cache = {}  # series.key -> activity computed so far; the stack only grows under one key


def run(series, params):
    d = series.data
    prev = _cache.get(series.key)
    n0 = min(len(prev), len(d)) if prev is not None else 0
    act = np.empty(len(d), np.float32)
    act[:n0] = prev[:n0] if n0 else act[:0]
    if n0 == 0 and len(d):
        act[0], n0 = 0.0, 1
    for i in range(n0, len(d)):
        act[i] = cv2.absdiff(d[i], d[i - 1]).mean()
    _cache.clear()
    _cache[series.key] = act
    return {"activity": act, "gate": act > params["gate"]}


def settings(parent=None):
    # Qt and the player are imported here, not at module top, so a batch script can import run()
    # without either installed.
    from sieve_player import ParamWidget, Trace

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.gate = self.add_float("gate", 0.0, 30.0, DEFAULTS["gate"])
            self.plot = Trace(rows=5)
            self.layout().addWidget(self.plot)
            self.result = None
            self.changed.connect(self._relevel)   # the gate line moves with the slider, before the rerun lands
            self.plot.levelDragged.connect(lambda v: self.gate.setValue(round(v * 100)))   # and the slider with the line

        def _relevel(self):
            if self.result is not None:
                self.plot.set_series(self.result["activity"], self.plot.start, self.result["gate"], self.params()["gate"])

        def show_result(self, result, start, fps):
            self.result = result
            self.plot.set_series(result["activity"], start, result["gate"], self.params()["gate"])

        def set_playhead(self, row):
            self.plot.playhead = row
            self.plot.update()

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray

    sys.exit(play([gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
