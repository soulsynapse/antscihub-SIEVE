"""Series tool: one number per row from a frame node's stack, by a chosen method, gated to a band; gray or mask in, signal and gate out.

The reduction is a decision, so it is a knob here and not inside the tool that measured: `mean`, `sum` and
`max` of the row's pixels, `count` of its nonzero pixels, or `fraction`, the count over the row's pixel count.
The walk folds each row to the four numbers every method is made of, so the window holds (T, 4) and never
the planes, and the method is picked at run() over that: changing it reruns on the folded stack.

`lo` and `hi` are the handles on the trace, and only the handles: no knob. A row is gated when its
value lies between them, and when `lo` has been dragged above `hi` the band is inside out: the rows
outside instead, as a node's band and inrange's hue band wrap. No invert switch; the handles say it. A
handle at the top of the trace is infinity, so the default band, 0 to infinity, gates every row.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS = "reduce", "series", ("gray", "mask")   # no PRODUCES: the result is read by the player, never by a wire
METHODS = ("mean", "sum", "max", "count", "fraction")
DEFAULTS = {"method": "mean", "lo": 0.0, "hi": float("inf")}


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
        """`lo` and `hi` are params without a row: the trace's handles are their only control, and
        the gate on the trace follows when the rerun lands."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_choice("method", METHODS, DEFAULTS["method"])
            self.plot = Trace(rows=5, levels=2)
            self.plot.levels[:] = [DEFAULTS["lo"], DEFAULTS["hi"]]
            self.layout().addWidget(self.plot)
            for i, k in enumerate(("lo", "hi")):
                self._get[k] = lambda i=i: self.plot.levels[i]
                self._set[k] = lambda v, i=i: self._set_level(i, float(v))
            self.plot.levelDragged.connect(lambda _i, _v: self.changed.emit())

        def _set_level(self, i, v):
            if v != self.plot.levels[i]:
                self.plot.levels[i] = v
                self.plot.update()
                self.changed.emit()

        def show_result(self, result, start, fps):
            self.plot.set_series(result["signal"], start, result["gate"])

        def set_playhead(self, row):
            self.plot.set_playhead(row)

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, motion

    sys.exit(play([gray, motion, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
