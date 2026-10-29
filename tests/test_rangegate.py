"""rangegate: the band between the handles, inside out once they cross; the trace's handles move the knobs."""
import os

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player.graph import Series  # noqa: E402
from tools import rangegate  # noqa: E402


def test_band_between_the_handles_and_outside_once_they_cross():
    s = Series(np.array([0.0, 2.0, 5.0, 9.0, 20.0]), "k", 0, 30.0)
    assert rangegate.run(s, {"lo": 1.0, "hi": 10.0})["gate"].tolist() == [False, True, True, True, False]
    assert rangegate.run(s, {"lo": 10.0, "hi": 1.0})["gate"].tolist() == [True, False, False, False, True]
    assert rangegate.run(s, {"lo": 5.0, "hi": 5.0})["signal"].tolist() == s.data.tolist()   # the signal passes through


def test_dragging_a_handle_moves_its_knob():
    QApplication.instance() or QApplication([])
    w = rangegate.settings()
    w.set_params({"lo": 1.0, "hi": 10.0})
    w.show_result(rangegate.run(Series(np.arange(5.0), "k", 0, 30.0), {"lo": 1.0, "hi": 10.0}), 0, 30.0)
    assert w.plot.levels == [1.0, 10.0]
    w.plot.levelDragged.emit(0, 3.5)
    assert w.params() == {"lo": 3.5, "hi": 10.0} and w.plot.levels == [3.5, 10.0]   # the knob, and the handle back from it


def test_the_knobs_reach_the_signal_and_a_saved_value_whatever_their_units():
    QApplication.instance() or QApplication([])
    w = rangegate.settings()
    w.set_params({"lo": 1.0, "hi": 5000.0})
    assert w.params() == {"lo": 1.0, "hi": 5000.0}                     # not clamped to the default reach
    sig = np.array([0.0, 2.0e5, 1.0e5])
    w.show_result(rangegate.run(Series(sig, "k", 0, 30.0), w.params()), 0, 30.0)
    w.plot.levelDragged.emit(1, 1.5e5)
    assert w.params() == {"lo": 1.0, "hi": 1.5e5} and w.plot.levels == [1.0, 1.5e5]
