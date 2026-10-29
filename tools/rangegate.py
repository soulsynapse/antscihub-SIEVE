"""Series tool: gate a signal to a band between two handles; signal in, the same signal and a gate out.

`lo` and `hi` are the handles on the trace. A row is gated when its value lies between them, and
when `lo` has been dragged above `hi` the band is inside out: the rows outside instead, as
inrange's hue band wraps. No invert switch; the handles say it.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "rangegate", "series", "signal", "signal"
DEFAULTS = {"lo": 1.0, "hi": 10.0}


def run(series, params):
    s = np.asarray(series.data, np.float32)
    lo, hi = params["lo"], params["hi"]
    gate = (s >= lo) & (s <= hi) if lo <= hi else (s >= lo) | (s <= hi)
    return {"signal": s, "gate": gate}


def settings(parent=None):
    from sieve_player import ParamWidget, Trace  # only the GUI needs the player

    class _Widget(ParamWidget):
        """The handles are the control; the knobs follow their reach. A signal is in whatever units the
        upstream tool measured, so the knobs' range is reset to cover the signal and the handles on
        every result, and before a saved value lands, or the knob would clamp the handle to a reach
        chosen for some other signal."""
        STEPS = 100            # knob steps per unit: add_float's two decimals
        TOP = (2**31 - 1) / STEPS   # QSlider's range is int

        def __init__(self, parent=None):
            super().__init__(parent)
            self.knobs = [self.add_float(k, 0.0, DEFAULTS["hi"], DEFAULTS[k]) for k in ("lo", "hi")]
            self.plot = Trace(rows=5, levels=2)
            self.layout().addWidget(self.plot)
            self.result = None
            self.changed.connect(self._relevel)   # the handles move with the knobs, before the rerun lands
            self.plot.levelDragged.connect(self._handle_dragged)   # and the knobs with the handles

        def _reach(self, *values):
            top = min(max(float(v) for v in (*values, *self.plot.levels, 0.0)), self.TOP)
            for s in self.knobs:
                s.setRange(0, round(top * self.STEPS))

        def _handle_dragged(self, i, v):
            self._reach(v)
            self.knobs[i].setValue(round(v * self.STEPS))

        def set_params(self, params):
            self._reach(*params.values())
            super().set_params(params)

        def _levels(self):
            p = self.params()
            return (p["lo"], p["hi"])

        def _relevel(self):
            if self.result is not None:
                self.plot.set_series(self.result["signal"], self.plot.start, self.result["gate"], self._levels())

        def show_result(self, result, start, fps):
            self.result = result
            s = result["signal"]
            self._reach(s.max() if len(s) else 0.0, *self._levels())
            self.plot.set_series(s, start, result["gate"], self._levels())

        def set_playhead(self, row):
            self.plot.set_playhead(row)

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, motion, reduce

    sys.exit(play([gray, motion, reduce, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
