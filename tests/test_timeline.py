"""The strip draws the pinned series at its rows over the clip's axis."""
import os

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import theme  # noqa: E402
from sieve_player.timeline import Strip  # noqa: E402


def test_a_series_is_drawn_at_its_rows_and_a_column_is_its_rows_envelope():
    QApplication.instance() or QApplication([])
    s = Strip()
    s.resize(100, s.H)
    s.set_count(1000, 30.0)
    s.set_series(np.r_[np.zeros(300), np.full(100, 10.0), np.zeros(100)], 400, np.r_[np.zeros(400, bool), np.ones(100, bool)])
    img = s.grab().toImage()
    ground = img.pixelColor(20, s.H // 2)                   # before the series' first row: the field alone
    y_top, y_body = s.GRAB + 2, s.H - 4
    green = lambda c: c.green() > c.red() and c.green() > ground.green()
    assert green(img.pixelColor(75, y_top))                 # rows 700..799 at full height, in the gate's green
    assert img.pixelColor(50, y_top) == ground              # a zero row draws at the bottom only
    assert img.pixelColor(60, s.H // 2) == ground           # a column that is one plateau is its line, not a fill
    assert green(img.pixelColor(85, y_body)) and img.pixelColor(50, y_body) == ground   # the gated columns alone are washed
    s.set_series(np.array([1.0, 1.0, 1.0]), 100)
    c = s.grab().toImage().pixelColor(10, y_top)
    assert c.blue() > c.red() and c.green() > c.red()       # no gate: a plain series, teal
