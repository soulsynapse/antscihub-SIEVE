"""Series tool: one number per row from a frame node's stack, by a chosen method, gated to a band; gray or mask in, signal and gate out.

The reduction is a decision, so it is a knob here and not inside the tool that measured: `mean`, `sum` and
`max` of the row's pixels, `count` of its nonzero pixels, or `fraction`, the count over the row's pixel count.
The walk folds each row to the four numbers every method is made of, so the window holds (T, 4) and never
the planes, and the method is picked at run() over that: changing it reruns on the folded stack.

`lo` and `hi` are the handles on the trace. A row is gated when its value lies between them, and when
`lo` has been dragged above `hi` the band is inside out: the rows outside instead, as a node's band and
inrange's hue band wrap. No invert switch; the handles say it.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS = "reduce", "series", ("gray", "mask")   # no PRODUCES: the result is read by the player, never by a wire
METHODS = ("mean", "sum", "max", "count", "fraction")
DEFAULTS = {"method": "mean", "lo": 1.0, "hi": 10.0}


def fold(frame):
    """A row's [sum, max, nonzero count, pixel count], float64."""
    f = np.asarray(frame)
    return np.array([f.sum(dtype=np.float64), f.max(), np.count_nonzero(f), f.size], np.float64)


def run(series, params):
    d = np.asarray(series.data, np.float64).reshape(len(series.data), 4)
    total, top, count, n = d.T
    m = params["method"]
    if m == "mean":
        s = total / np.maximum(n, 1)
    elif m == "sum":
        s = total
    elif m == "max":
        s = top
    elif m == "count":
        s = count
    elif m == "fraction":
        s = count / np.maximum(n, 1)
    else:
        raise ValueError(f"reduce: no method {m!r}; one of {METHODS}")
    s = np.asarray(s, np.float32)
    lo, hi = params["lo"], params["hi"]
    gate = (s >= lo) & (s <= hi) if lo <= hi else (s >= lo) | (s <= hi)
    return {"signal": s, "gate": gate}


def settings(parent=None):
    from sieve_player import ParamWidget, Trace  # only the GUI needs the player

    class _Widget(ParamWidget):
        """The handles are the control; the knobs follow their reach. A signal is in whatever units the
        method makes, so the knobs' range is reset to cover the signal and the handles on every result,
        and before a saved value lands, or the knob would clamp the handle to a reach chosen for some
        other signal."""
        STEPS = 100            # knob steps per unit: add_float's two decimals
        TOP = (2**31 - 1) / STEPS   # QSlider's range is int

        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_choice("method", METHODS, DEFAULTS["method"])
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
            self._reach(*(v for k, v in params.items() if k in ("lo", "hi")))
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
    from tools import gray, motion

    sys.exit(play([gray, motion, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
