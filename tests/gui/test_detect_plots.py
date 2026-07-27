"""The detection plots: the gesture boundary, unbounded drags, the 1 px floor.

Each test pins one of item 5's load-bearing claims. The gesture boundary
(8 px grabs, 9 px scrubs) is what makes one dragless gesture serve two
meanings; unbounded-vs-clamped is the difference between a band that shapes a
signal and a frequency band the transform would silently correct; the 1 px
gate floor is what keeps a single-frame detection visible at any zoom; and
solo living in the state model is what keeps the composite's grid overlay and
the density plot from ever disagreeing about which block is soloed.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pytest
from PySide6.QtCore import QPointF
from pytestqt.qtbot import QtBot

from sieve.core.wavelet import default_freqs
from sieve.gui.band_plot import GRAB_PX
from sieve.gui.composite_view import StepCompositeView
from sieve.gui.count_plot import CountPlot
from sieve.gui.density_plot import DensityPlot
from sieve.gui.scalogram_plot import ScalogramPlot
from tests.gui import qt_input

pytestmark = pytest.mark.gui


def _capture(dest: list[tuple[float, float]]) -> Callable[[float, float], None]:
    """A typed slot for band signals — a bare lambda leaves pyright blind."""

    def slot(lo: float, hi: float) -> None:
        dest.append((lo, hi))

    return slot


FPS = 30.0
FRAMES = 600
BLOCKS = 64


def _density(qtbot: QtBot) -> DensityPlot:
    plot = DensityPlot()
    qtbot.addWidget(plot)
    plot.resize(800, 200)
    plot.set_span(0, FRAMES)
    rng = np.random.default_rng(7)
    plot.set_series(rng.uniform(0.0, 100.0, (FRAMES, BLOCKS)).astype(np.float32))
    return plot


class TestUnboundedVersusClamped:
    def test_dragging_the_value_handle_past_the_top_emits_inf(self, qtbot: QtBot) -> None:
        plot = _density(qtbot)
        plot.set_band(0.0, 50.0)
        emitted: list[tuple[float, float]] = []
        plot.band_changed.connect(_capture(emitted))
        committed: list[tuple[float, float]] = []
        plot.band_committed.connect(_capture(committed))

        x = float(plot.plot_rect().center().x())
        above = QPointF(x, plot.plot_rect().top() - 10.0)
        qt_input.press(plot, QPointF(x, plot.handle_y("hi")))
        qt_input.move(plot, above)
        qt_input.release(plot, above)

        assert emitted and math.isinf(emitted[-1][1]) and emitted[-1][1] > 0
        assert committed and math.isinf(committed[-1][1])

    def test_the_frequency_handle_clamps_to_the_bank_edge_instead(self, qtbot: QtBot) -> None:
        plot = ScalogramPlot()
        qtbot.addWidget(plot)
        plot.resize(800, 200)
        plot.set_span(0, FRAMES)
        freqs = default_freqs(FPS)
        plot.set_power(np.ones((len(freqs), FRAMES), np.float32), freqs, FPS)
        plot.set_band(1.0, 5.0)
        emitted: list[tuple[float, float]] = []
        plot.band_changed.connect(_capture(emitted))

        x = float(plot.plot_rect().center().x())
        qt_input.press(plot, QPointF(x, plot.handle_y("hi")))
        qt_input.move(plot, QPointF(x, plot.plot_rect().top() - 40.0))
        qt_input.release(plot, QPointF(x, plot.plot_rect().top() - 40.0))

        assert emitted and math.isfinite(emitted[-1][1])
        assert emitted[-1][1] == pytest.approx(float(freqs[-1]))


class TestTheGestureBoundary:
    def test_a_drag_starting_nine_px_from_a_handle_scrubs(self, qtbot: QtBot) -> None:
        plot = _density(qtbot)
        plot.set_band(0.0, 50.0)
        bands: list[tuple[float, float]] = []
        plot.band_changed.connect(_capture(bands))
        presses: list[int] = []
        plot.pressed.connect(presses.append)

        x = float(plot.plot_rect().center().x())
        start = QPointF(x, plot.handle_y("hi") + GRAB_PX + 1.0)
        qt_input.press(plot, start)
        qt_input.move(plot, QPointF(x + 30.0, start.y()))
        qt_input.release(plot, QPointF(x + 30.0, start.y()))

        assert presses and not bands

    def test_at_eight_px_the_same_drag_grabs_the_handle(self, qtbot: QtBot) -> None:
        plot = _density(qtbot)
        plot.set_band(0.0, 50.0)
        bands: list[tuple[float, float]] = []
        plot.band_changed.connect(_capture(bands))
        presses: list[int] = []
        plot.pressed.connect(presses.append)

        x = float(plot.plot_rect().center().x())
        start = QPointF(x, plot.handle_y("hi") + GRAB_PX)
        qt_input.press(plot, start)
        qt_input.move(plot, QPointF(x, start.y() + 20.0))
        qt_input.release(plot, QPointF(x, start.y() + 20.0))

        assert bands and not presses


class TestTheGateFloor:
    @pytest.mark.parametrize("width", [80, 300, 1600])
    def test_a_one_frame_detection_paints_at_least_one_px(self, qtbot: QtBot, width: int) -> None:
        plot = CountPlot()
        qtbot.addWidget(plot)
        plot.resize(width, 150)
        plot.set_span(0, FRAMES)
        plot.set_series(np.zeros(FRAMES, np.float32), region_blocks=BLOCKS, armed=True)
        gate = np.zeros(FRAMES, bool)
        gate[300] = True
        plot.set_gate(gate)

        rects = plot.gate_rects()
        assert len(rects) == 1
        assert rects[0].width() >= 1.0


def _grid_view(qtbot: QtBot) -> StepCompositeView:
    view = StepCompositeView()
    qtbot.addWidget(view)
    view.resize(420, 360)
    view.set_grid_visible(True)
    view.set_grid(4, 4)
    view.set_block_state(np.zeros(16, np.float32), np.zeros(16, bool), None)
    view.show()
    return view


class TestSoloLivesInTheStateModel:
    def test_a_click_emits_and_does_not_apply_itself(self, qtbot: QtBot) -> None:
        """Clicking the same block twice emits the same index twice — the
        pane's own solo moved nowhere, because only `set_block_state` moves it."""
        view = _grid_view(qtbot)
        emitted: list[object] = []
        view.solo_toggled.connect(emitted.append)

        pane = view.pane
        g = pane.grid_rect()
        cell = QPointF(g.left() + g.width() * 3.0 / 8.0, g.top() + g.height() * 3.0 / 8.0)
        block = pane.block_at(cell)
        qt_input.click(pane, cell)
        qt_input.click(pane, cell)
        assert emitted == [block, block]

    def test_once_the_state_model_confirms_the_same_click_untoggles(self, qtbot: QtBot) -> None:
        view = _grid_view(qtbot)
        pane = view.pane
        g = pane.grid_rect()
        cell = QPointF(g.left() + g.width() * 3.0 / 8.0, g.top() + g.height() * 3.0 / 8.0)
        block = pane.block_at(cell)
        assert block is not None
        view.set_block_state(np.zeros(16, np.float32), np.zeros(16, bool), block)
        emitted: list[object] = []
        view.solo_toggled.connect(emitted.append)

        qt_input.click(pane, cell)
        assert emitted == [None]
