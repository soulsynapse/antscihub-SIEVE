"""Series tool: one number per row from a frame node's stack, by a chosen method; gray or mask in, signal out.

The reduction is a decision, so it is a knob here and not inside the tool that measured: `mean`, `sum` and
`max` of the row's pixels, `count` of its nonzero pixels, or `fraction`, the count over the row's pixel count.
"""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "reduce", "series", ("gray", "mask"), "signal"
METHODS = ("mean", "sum", "max", "count", "fraction")
DEFAULTS = {"method": "mean"}


def run(series, params):
    flat = np.asarray(series.data).reshape(len(series.data), -1)
    m = params["method"]
    if m == "mean":
        s = flat.mean(axis=1)
    elif m == "sum":
        s = flat.sum(axis=1, dtype=np.float64)
    elif m == "max":
        s = flat.max(axis=1)
    elif m == "count":
        s = np.count_nonzero(flat, axis=1)
    elif m == "fraction":
        s = np.count_nonzero(flat, axis=1) / max(flat.shape[1], 1)
    else:
        raise ValueError(f"reduce: no method {m!r}; one of {METHODS}")
    return {"signal": np.asarray(s, np.float32)}


def settings(parent=None):
    from sieve_player import ParamWidget, Trace  # only the GUI needs the player

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_choice("method", METHODS, DEFAULTS["method"])
            self.plot = Trace(rows=5)
            self.layout().addWidget(self.plot)

        def show_result(self, result, start, fps):
            self.plot.set_series(result["signal"], start)

        def set_playhead(self, row):
            self.plot.set_playhead(row)

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, motion

    sys.exit(play([gray, motion, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
