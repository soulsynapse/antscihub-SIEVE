"""reduce: each method over a row's pixels, one float per row, from the four numbers the fold keeps; the band between the handles gates it, inside out once they cross; the trace's handles move the knobs."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player.graph import Series  # noqa: E402
from tools import reduce  # noqa: E402

BAND = {"lo": 1.0, "hi": 10.0}


def test_each_method_over_the_rows_pixels():
    d = np.zeros((2, 4, 4), np.uint8)
    d[1, :2, :2] = 200                                     # row 1: four of sixteen pixels at 200
    folded = np.stack([reduce.fold(f) for f in d])
    assert folded.shape == (2, 4) and folded[1].tolist() == [800.0, 200.0, 4.0, 16.0]
    s = Series(folded, "k", 0, 30.0)
    expect = {"mean": [0.0, 50.0], "sum": [0.0, 800.0], "max": [0.0, 200.0], "count": [0.0, 4.0], "fraction": [0.0, 0.25]}
    for m, want in expect.items():
        out = reduce.run(s, {"method": m, **BAND})["signal"]
        assert out.dtype == np.float32 and out.tolist() == want, m
    with pytest.raises(ValueError):
        reduce.run(s, {"method": "median", **BAND})


def folded(values):
    """A stack whose max per row is `values`: the max method reads it back."""
    return Series(np.array([[0.0, v, 0.0, 1.0] for v in values]), "k", 0, 30.0)


def test_band_between_the_handles_and_outside_once_they_cross():
    s = folded([0.0, 2.0, 5.0, 9.0, 20.0])
    assert reduce.run(s, {"method": "max", "lo": 1.0, "hi": 10.0})["gate"].tolist() == [False, True, True, True, False]
    assert reduce.run(s, {"method": "max", "lo": 10.0, "hi": 1.0})["gate"].tolist() == [True, False, False, False, True]


def test_dragging_a_handle_moves_its_knob():
    QApplication.instance() or QApplication([])
    w = reduce.settings()
    w.set_params({"method": "max", **BAND})
    w.show_result(reduce.run(folded(np.arange(5.0)), w.params()), 0, 30.0)
    assert w.plot.levels == [1.0, 10.0]
    w.plot.levelDragged.emit(0, 3.5)
    assert w.params() == {"method": "max", "lo": 3.5, "hi": 10.0} and w.plot.levels == [3.5, 10.0]   # the knob, and the handle back from it


def test_the_knobs_reach_the_signal_and_a_saved_value_whatever_their_units():
    QApplication.instance() or QApplication([])
    w = reduce.settings()
    w.set_params({"method": "max", "lo": 1.0, "hi": 5000.0})
    assert w.params() == {"method": "max", "lo": 1.0, "hi": 5000.0}                     # not clamped to the default reach
    w.show_result(reduce.run(folded([0.0, 2.0e5, 1.0e5]), w.params()), 0, 30.0)
    w.plot.levelDragged.emit(1, 1.5e5)
    assert w.params()["hi"] == 1.5e5 and w.plot.levels == [1.0, 1.5e5]
