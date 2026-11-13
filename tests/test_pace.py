"""The header's figure: a rate off the worker's signals and a clock, with nothing attached to the probe."""
import itertools
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.pace import Pace  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tests.test_graph import TOOLS, Dec, gray  # noqa: E402
from tests.test_plot import series  # noqa: E402
from tools import gray as plate_gray  # noqa: E402


def test_the_rate_is_the_rows_after_a_walks_first_signal_over_the_clock_and_a_lower_count_opens_a_walk():
    ticks = iter([0.0, 3.0, 10.0, 11.0])
    p = Pace(clock=lambda: next(ticks))
    p.row("window", 1, 10, 1, 0)
    p.row("window", 10, 10, 10, 0)
    f = p.figure(30.0, 300)
    assert (f.multiple, f.what, f.seconds, f.clip_s) == (pytest.approx(0.1), "takes", pytest.approx(100.0), 10.0)
    p.row("window", 1, 10, 0, 0)
    p.row("window", 3, 10, 0, 0)
    f = p.figure(30.0, 300)
    assert (f.done, f.held, f.multiple, f.what, f.seconds) == (3, 3, pytest.approx(2 / 30), "", None)


def test_the_worker_s_signals_give_the_figure_with_no_consumer_on_the_probe_and_a_clip_time_from_a_cold_walk_alone():
    """The window walk's turns are taken on this thread, the worker's never started, so no scrub
    reaches a row before the walk does."""
    QApplication.instance() or QApplication([])
    head = series("head", lambda v: np.arange(len(v), dtype=np.float64))
    dec = Dec()
    dec.count = 200
    g = Graph(D.from_tools([gray, head]), dec, {**TOOLS, "head": head})
    w = Worker(g)
    ticks = itertools.count()
    pace = Pace(clock=lambda: float(next(ticks)))
    w.walked.connect(lambda *row: pace.row("window", *row))

    def walk():
        g.serving("walk", "window")
        w._win.begin(100, 40)
        while w._win.i < w._win.length:
            w._win.turn()
        return pace.figure(g.fps, g.count)

    cold = walk()
    assert (cold.ran, cold.what) == (40, "takes") and cold.seconds == pytest.approx(cold.clip_s / cold.multiple)
    again = walk()
    assert (again.ran, again.held, again.what) == (0, 40, "") and again.multiple is not None
    assert g.on_event is None


def test_the_header_shows_the_pace_s_figure_and_a_click_on_it_opens_the_monitor(tmp_path):
    QApplication.instance() or QApplication([])
    D.save(D.from_tools([plate_gray], clip(tmp_path / "v.avi")), tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [plate_gray])
    win.show()
    win._paced("window", 1, 10, 1, 0)
    assert win.header.figure.figure == win.pace.figure(win.fps, win.count)
    win.header.figure.click()
    assert win.__dict__["_dev_windows"]["monitor"].isVisible()
    win.close()
