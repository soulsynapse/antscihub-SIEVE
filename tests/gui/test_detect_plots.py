"""The detection plots: the gesture boundary, unbounded drags, the 1 px floor.

Each test pins one of item 5's load-bearing claims. The gesture boundary
(8 px grabs, 9 px scrubs) is what makes one dragless gesture serve two
meanings; unbounded-vs-clamped is the difference between a band that shapes a
signal and a frequency band the transform would silently correct; the 1 px
gate floor is what keeps a single-frame detection visible at any zoom; and
solo living in the state model is what keeps the composite's grid overlay and
the density plot from ever disagreeing about which block is soloed.

The count axis's claims are here for the same reason: an axis that ran to the
region's block count left the only tunable graph unreadable at a realistic
block count, and the three rules that make autoscaling safe — the band is
unioned in, a drag freezes the frame, the ceiling in force is written on the
plot — are each a way the naive version loses something. The first two lose
the handle; the third loses the reader's ability to tell two tunings apart.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np
import pytest
from PySide6.QtCore import QPointF
from pytestqt.qtbot import QtBot

from sieve.core.ops.wavelet import default_freqs
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


#: A peak nowhere near the region's block count — the realistic case, and the
#: one a 0..B axis drew on the bottom pixel row.
PEAK = 4.0


def _count(qtbot: QtBot, peak: float = PEAK) -> CountPlot:
    plot = CountPlot()
    qtbot.addWidget(plot)
    plot.resize(800, 200)
    plot.set_span(0, FRAMES)
    series = np.zeros(FRAMES, np.float32)
    series[FRAMES // 2] = peak
    plot.set_series(series, region_blocks=BLOCKS, armed=True)
    return plot


class TestTheCountAxis:
    def test_the_peak_reaches_the_top_of_the_plot_not_the_floor(self, qtbot: QtBot) -> None:
        """4 blocks of 64 fills the plot, because the axis is the data.

        On the old 0..B axis this sat 6% up from the bottom, which at a
        realistic block count is the bottom pixel row.
        """
        plot = _count(qtbot)
        r = plot.plot_rect()

        height_used = (r.bottom() - plot.y_of(PEAK)) / r.height()

        assert height_used > 0.9

    def test_a_threshold_above_the_data_keeps_its_value_reachable(self, qtbot: QtBot) -> None:
        """The band is unioned into the range, so the handle is at 40, not clamped.

        This is the scrub case: a threshold placed against a loud stretch, then
        the window moves somewhere quiet. Without the union the handle pins to
        the frame and reads as the axis top — a value the user never set, and
        one they could only correct by scrubbing back.
        """
        plot = _count(qtbot)
        plot.set_band(0.0, 40.0)

        assert plot.value_of(plot.handle_y("hi")) == pytest.approx(40.0, rel=1e-3)

    def test_a_held_handle_does_not_chase_its_own_rescale(self, qtbot: QtBot) -> None:
        """Two moves to the same y emit the same count: the axis froze at press.

        Unfrozen, the range widens to hold the handle and the handle is placed
        through the range — so a stationary mouse walks the value down a
        geometric series, one step per mouse-move event.
        """
        plot = _count(qtbot)
        plot.set_band(0.0, 40.0)
        emitted: list[tuple[float, float]] = []
        plot.band_changed.connect(_capture(emitted))

        r = plot.plot_rect()
        x = float(r.center().x())
        target = QPointF(x, r.top() + r.height() * 0.25)
        qt_input.press(plot, QPointF(x, plot.handle_y("hi")))
        qt_input.move(plot, target)
        qt_input.move(plot, target)
        qt_input.release(plot, target)

        assert len(emitted) == 2
        assert emitted[0][1] == pytest.approx(emitted[1][1])


class TestTheAxisSaysWhichCeiling:
    """Rule 6: an autoscaled plot must not be readable as a full-scale one."""

    def test_the_autoscaled_ceiling_is_the_one_reported(self, qtbot: QtBot) -> None:
        """The label names the data ceiling, not the region — and both numbers."""
        plot = _count(qtbot)

        assert plot.scale_label() == f"0-{round(PEAK * 1.06)} of {BLOCKS} blocks"
        assert "full" not in plot.scale_label()

    def test_a_peak_at_the_region_size_reads_as_full(self, qtbot: QtBot) -> None:
        """Capped at B, the label says so — the regime the fixed axis always had."""
        plot = _count(qtbot, peak=float(BLOCKS))

        assert plot.scale_label() == f"0-{BLOCKS} of {BLOCKS} blocks · full"

    def test_the_label_follows_the_frozen_axis_through_a_drag(self, qtbot: QtBot) -> None:
        """One `_range` feeds both the geometry and the reading of it.

        A label re-derived independently would report a ceiling the handles are
        not actually placed against for the length of every gesture.
        """
        plot = _count(qtbot)
        plot.set_band(0.0, 40.0)
        during = f"0-{round(40.0 * 1.06)} of {BLOCKS} blocks"
        assert plot.scale_label() == during

        r = plot.plot_rect()
        x = float(r.center().x())
        qt_input.press(plot, QPointF(x, plot.handle_y("hi")))
        qt_input.move(plot, QPointF(x, r.bottom() - 1.0))

        assert plot.scale_label() == during

        qt_input.release(plot, QPointF(x, r.bottom() - 1.0))

        assert plot.scale_label() != during


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
    def test_a_gesture_emits_and_does_not_apply_itself(self, qtbot: QtBot) -> None:
        """The pane asks; only `set_block_state` moves the marker it draws.

        Hover is now the gesture, so this is the same claim the click version
        made and a livelier way to break it: a pane that painted its own hover
        would disagree with the density plot for a frame on every crossing
        rather than once per click.
        """
        view = _grid_view(qtbot)
        emitted: list[object] = []
        view.solo_toggled.connect(emitted.append)

        pane = view.pane
        g = pane.grid_rect()
        first = QPointF(g.left() + g.width() * 3.0 / 8.0, g.top() + g.height() * 3.0 / 8.0)
        second = QPointF(g.left() + g.width() * 7.0 / 8.0, g.top() + g.height() * 3.0 / 8.0)
        qt_input.move(pane, first)
        qt_input.move(pane, second)

        assert emitted == [pane.block_at(first), pane.block_at(second)]
        assert pane.solo is None, "the pane applied its own gesture"

    def test_the_model_holding_a_block_is_never_asked_for_it_again(self, qtbot: QtBot) -> None:
        """The dedupe is against what the model applied, not against a private
        record of what was emitted — so hovering onto the block already soloed
        asks for nothing, and every graph is spared a repaint."""
        view = _grid_view(qtbot)
        pane = view.pane
        g = pane.grid_rect()
        cell = QPointF(g.left() + g.width() * 3.0 / 8.0, g.top() + g.height() * 3.0 / 8.0)
        block = pane.block_at(cell)
        assert block is not None
        view.set_block_state(np.zeros(16, np.float32), np.zeros(16, bool), block)
        emitted: list[object] = []
        view.solo_toggled.connect(emitted.append)

        qt_input.move(pane, cell)
        assert emitted == []
        # Leaving asks for none: nothing is pinned, so the model's block goes.
        qt_input.leave(pane)
        assert emitted == [None]
