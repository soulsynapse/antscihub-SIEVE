"""Dummy series: a constant `value` per row of the window, gated above `gate`. Draws the value on
the frame so `draw` has a referent."""
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS = "flat", "series", "gray"
DEFAULTS = {"value": 1.0, "gate": 0.5}


def run(series, params):
    v = np.full(len(series.data), params["value"], np.float32)
    return {"value": v, "gate": v > params["gate"]}


def draw(painter, row, result, start):
    if result is not None:
        painter.drawText(8, 16, f"flat {result['value'][0]:.2f}")


def settings(parent=None):
    from sieve_player import ParamWidget, Trace

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_float("value", 0.0, 2.0, DEFAULTS["value"])
            self.add_float("gate", 0.0, 2.0, DEFAULTS["gate"])
            self.plot = Trace(rows=4)
            self.layout().addWidget(self.plot)

        def show_result(self, result, start, fps):
            self.plot.set_series(result["value"], start, result["gate"], self.params()["gate"])

        def set_playhead(self, row):
            self.plot.set_playhead(row)

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from dummies import to_gray

    sys.exit(play([to_gray, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
