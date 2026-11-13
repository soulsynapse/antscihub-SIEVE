"""The header's figure: a rate off the worker's signals and a clock, with nothing attached to the probe."""
import os
import time

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.pace import Pace  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tests.test_plot import series  # noqa: E402
from tools import gray  # noqa: E402


def walked(win, total, timeout=10.0):
    """The figure once the window lane has finished a walk of `total` rows begun after this call."""
    win.pace._walks.pop("window", None)
    t = time.perf_counter()
    while True:
        QApplication.processEvents()
        f = win.pace.figure(win.fps, win.count)
        if f is not None and f.over and f.total == total:
            return f
        assert time.perf_counter() - t < timeout, f
        time.sleep(0.002)


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


def test_the_header_gives_the_figure_with_no_consumer_on_the_probe_and_a_clip_time_from_a_cold_walk_alone(tmp_path):
    QApplication.instance() or QApplication([])
    head = series("head", lambda v: np.arange(len(v), dtype=np.float64))
    D.save(D.from_tools([gray, head], clip(tmp_path / "v.avi", n=400)), tmp_path / "doc.json")
    win = PlayerWindow(str(tmp_path / "doc.json"), "t", [gray, head])
    win.show()
    win.graph.on_event = None
    walked(win, 300)                                            # the open's walk, rows 0 to 299
    win.set_window(300, 40)
    cold = walked(win, 40)
    assert cold.ran >= 39 and cold.what == "takes" and cold.seconds == pytest.approx(cold.clip_s / cold.multiple)
    win.worker.set_window(300, 40)
    again = walked(win, 40)
    assert (again.ran, again.held, again.what) == (0, 40, "") and again.multiple is not None
    assert win.header.figure.figure == again and win.graph.on_event is None
    win.header.figure.click()
    assert win.__dict__["_dev_windows"]["monitor"].isVisible()
    win.close()
