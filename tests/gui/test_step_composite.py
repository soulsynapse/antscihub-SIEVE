"""The step composite: selection targeting, the refresh guard, and the HUD.

Four claims, each a distinct way the composite could quietly wreck the tab.
A wrong target would compose frames of a step the user did not select; a
playhead refresh that ran while a window render was outstanding would
displace the graphs' render from the runner's one pending slot and the
series would never arrive; a refresh that cleared the HUD would erase
the window's cost series thirty times a second during playback; and a
pair that painted only at `render_finished` would leave the pane blank
for the whole first window render of every source.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QImage, QKeyEvent
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.core.types import ROI
from sieve.gui.band_plot import PANEL
from sieve.gui.composite_view import GRID_STEPS, StepCompositeView
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.player import VideoPlayer

pytestmark = pytest.mark.gui


class _StubRunner(QObject):
    """A runner that records submissions instead of rendering.

    The tab only reads `revision` and calls the two request methods; the
    signals exist so `_connect` finds what it wires. Everything a test
    asserts about ordering is in `window_renders` and `frame_renders`.
    """

    frame_cost = Signal(int, float)
    render_started = Signal(int)
    render_finished = Signal(object)
    render_failed = Signal(str)
    opened = Signal()
    open_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.revision = 0
        self.window_renders: list[object] = []
        self.frame_renders: list[int] = []
        self.consumers: list[object] = []
        self.frame_consumers: list[object] = []

    def request_render(
        self, pipeline: object, window: object, replicate: object, consumer: object = None
    ) -> bool:
        self.revision += 1
        self.window_renders.append(pipeline)
        self.consumers.append(consumer)
        return True

    def request_frame(
        self, pipeline: object, index: int, replicate: object, consumer: object = None
    ) -> bool:
        self.revision += 1
        self.frame_renders.append(index)
        self.frame_consumers.append(consumer)
        # The real runner's idle path: `_issue` emits `render_started`
        # synchronously, before `request_frame` returns. The HUD test below
        # pins a race that only exists on this path, so the stub must keep it.
        self.render_started.emit(self.revision)
        return True


@pytest.fixture
def player(qapp: object) -> Iterator[VideoPlayer]:
    del qapp
    instance = VideoPlayer()
    yield instance
    instance.shutdown()


@pytest.fixture
def stub() -> _StubRunner:
    return _StubRunner()


@pytest.fixture
def tab(
    qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument, stub: _StubRunner
) -> Iterator[FilterTab]:
    instance = FilterTab(player, document, stub, metrics=MetricBus())  # type: ignore[arg-type]
    qtbot.addWidget(instance)
    yield instance
    # The tab owns the detector thread, so it carries the same
    # shutdown obligation the player and the runner do. Without
    # this every tab built here leaks a QThread and the suite
    # wedges a few modules later.
    instance.shutdown()


def test_selection_defaults_to_the_tail_and_targets_the_deepest_rendered_step(
    tab: FilterTab,
) -> None:
    """Full current state is a selection, not a mode.

    The stack always has a selected step, defaulting to the tail — and a
    tab-side selection (windowed count has no node) must resolve the
    composite to the deepest step the render actually produced, which the
    caption says out loud. Clicking a card retargets, and the marker follows
    the model rather than the click.
    """
    assert tab.selected_step == "windowed_count"
    assert tab.composite.caption == "Block signal (deepest rendered)"

    card = tab.stack.card_for("rescale")
    assert card is not None and not card.selected
    card.mousePressEvent(None)

    assert tab.selected_step == "rescale"
    assert tab.composite.caption == "Rescale"
    assert card.selected
    tail = tab.stack.card_for("windowed_count")
    assert tail is not None and not tail.selected


def test_a_playhead_refresh_never_displaces_a_pending_window_render(
    tab: FilterTab, stub: _StubRunner, player: VideoPlayer
) -> None:
    """The guard the graphs depend on.

    The runner holds one pending request; a stream of single-frame composite
    refreshes issued while a window render is outstanding would overwrite it
    and the series would never arrive. So: after a resubmit, playhead moves
    must submit nothing — and once the render reports back, the next move
    must submit exactly the frame refresh it suppressed.
    """
    stub.opened.emit()  # the tab's own resubmit path, as the runner announces it
    assert len(stub.window_renders) == 1

    frame = QImage(160, 120, QImage.Format.Format_RGB32)
    player.frame_changed.emit(5, frame)
    player.frame_changed.emit(6, frame)
    assert stub.frame_renders == [], "a refresh ran while the graphs' render was outstanding"

    stub.render_finished.emit(object())
    player.frame_changed.emit(7, frame)
    assert stub.frame_renders == [7]


def test_the_pair_paints_at_the_playhead_frame_not_at_render_finished(
    tab: FilterTab, stub: _StubRunner
) -> None:
    """The first composite must not cost a whole window render.

    The window render's consumer catches the pair the moment the playhead
    frame passes — usually the window's first frame — and the pane must
    paint it on that frame's cost tick, hundreds of frames before
    `render_finished`. v1 drew its frame near-instantly; a pane that waits
    for the full window is the regression this test pins.
    """
    stub.opened.emit()
    consumer = stub.consumers[-1]
    assert consumer is not None

    frames = {
        "rescale": np.full((8, 8), 100, np.uint8),
        "normalize": np.full((8, 8), 128, np.uint8),
        "block_signal": np.ones((2, 3), np.float32),
    }
    outputs = {
        step.node.node_id: SimpleNamespace(data=frames[step.step_id])
        for step in tab.chain.steps
        if step.node is not None
    }
    consumer(SimpleNamespace(index=0, outputs=outputs))  # type: ignore[operator]
    assert tab.composite.frames() == (None, None), "painted before the GUI thread heard"

    stub.frame_cost.emit(0, 5.0)
    base, over = tab.composite.frames()
    assert base is not None, "the pair waited for render_finished"
    # The default target is the block step, whose output is a grid, not an
    # image: the pane draws it itself, so `over` stays empty and the grid is on.
    assert over is None
    assert tab.composite.pane.grid_on


def test_a_composite_refresh_leaves_the_hud_series_alone(
    tab: FilterTab, stub: _StubRunner, player: VideoPlayer
) -> None:
    """Playback must not erase the window's cost series.

    A composite refresh is one frame at the playhead, served from the store;
    its `render_started` must not clear the HUD and its near-zero frame cost
    must not overwrite the render's real cost at that index. A window
    render's start, by contrast, still replaces the series — that contract
    stays the runner's.

    The stub emits `render_started` *inside* `request_frame`, as the idle
    runner does — which is exactly when the first refresh after a finished
    render runs. A tab that records the exemption only after the call
    returns hears that start unexempted and wipes the series it just
    collected.
    """
    stub.opened.emit()
    stub.render_started.emit(stub.revision)
    stub.frame_cost.emit(3, 25.0)
    stub.render_finished.emit(object())
    assert tab.hud.costs() == ((3, 25.0),)

    player.frame_changed.emit(3, QImage(160, 120, QImage.Format.Format_RGB32))
    assert stub.frame_renders == [3]
    stub.frame_cost.emit(3, 0.2)

    assert tab.hud.costs() == ((3, 25.0),), "the composite refresh touched the HUD"


def test_a_first_step_targets_base_is_the_replicates_crop(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument, player: VideoPlayer
) -> None:
    """The overlay says *where inside the replicate*, so the frame under it
    must be the replicate's crop, not the parent footage the graph never saw.

    The one composite base that comes from the player rather than the render
    is the first step's input, and the ROI is in source pixels (1000x800
    here) while the player frame may be a half-size proxy — so the crop must
    scale by the image's actual size.
    """
    card = tab.stack.card_for("rescale")
    assert card is not None
    card.mousePressEvent(None)

    document.add_roi(ROI(x=200, y=100, width=300, height=200))
    document.select(0)  # selection change resubmits the window render
    stub.render_finished.emit(object())  # so the playhead refresh below runs
    player.frame_changed.emit(3, QImage(500, 400, QImage.Format.Format_RGB32))

    grab = stub.frame_consumers[-1]
    assert grab is not None
    node = next(s.node for s in tab.chain.steps if s.step_id == "rescale")
    assert node is not None
    outputs = {node.node_id: SimpleNamespace(data=np.full((8, 8), 100, np.uint8))}
    grab(SimpleNamespace(index=3, outputs=outputs))  # type: ignore[operator]
    stub.frame_cost.emit(3, 0.1)

    base, _ = tab.composite.frames()
    assert base is not None
    assert (base.width(), base.height()) == (150, 100), "the crop ignored the proxy scale"


def test_border_alpha_zero_separates_blocks_and_equal_alphas_read_as_a_mass(
    qtbot: QtBot,
) -> None:
    """The see-through contract of the grid overlay.

    Ring and interior are disjoint pixel regions at independent alphas: with
    the border slider at zero, neighbouring in-band fills must leave bare
    background between them (separated blocks); raising the border to the
    fill's alpha must paint that seam (one mass). Pixels, not flags — a
    compositing change that blended ring over fill would pass any flag test
    and still break the equal-alphas read.
    """
    view = StepCompositeView()
    qtbot.addWidget(view)
    view.resize(400, 400)
    view.set_grid_visible(True)
    view.set_grid(2, 2)
    view.set_block_state(np.full(4, 5.0, np.float32), np.ones(4, bool), None)
    view.fill_slider.setValue(GRID_STEPS)  # 1.0
    view.line_slider.setValue(0)
    view.heat_slider.setValue(0)  # bare seams, not heat-coloured ones
    view.show()

    pane = view.pane
    g = pane.grid_rect()
    seam_x = int(g.left() + g.width() / 2.0)
    row_y = int(g.top() + g.height() / 4.0)
    strip = range(seam_x - 2, seam_x + 3)

    image = pane.grab().toImage()
    assert any(image.pixelColor(x, row_y) == PANEL for x in strip), (
        "no bare background at the seam — the blocks are not separated"
    )
    interior = image.pixelColor(int(g.left() + g.width() / 4.0), row_y)
    assert interior != PANEL, "the in-band interior is not filled"

    view.line_slider.setValue(GRID_STEPS)  # equal alphas
    image = pane.grab().toImage()
    assert all(image.pixelColor(x, row_y) != PANEL for x in strip), (
        "bare background survived equal alphas — the mass has seams"
    )


def test_the_heatmap_runs_cold_to_hot_and_borders_mark_only_detected_cells(
    qtbot: QtBot,
) -> None:
    """The two layers stay two layers.

    The heatmap colours *every* cell by value — cold at the bottom of the
    scale, hot at the top — regardless of the band; the border ring belongs
    to detected cells only. A regression that gated the heat on the band, or
    ringed every cell, passes any state test and lies on screen.
    """
    view = StepCompositeView()
    qtbot.addWidget(view)
    view.resize(400, 220)
    view.set_grid_visible(True)
    view.set_grid(1, 2)
    view.set_scale_max(10.0)
    # Left cell cold, right cell hot; neither in band.
    view.set_block_state(np.array([0.0, 10.0], np.float32), np.zeros(2, bool), None)
    view.heat_slider.setValue(GRID_STEPS)  # 1.0, so pixels are the ramp's own
    view.line_slider.setValue(GRID_STEPS)
    view.fill_slider.setValue(0)
    view.show()

    pane = view.pane
    g = pane.grid_rect()
    mid_y = int(g.top() + g.height() / 2.0)
    cold_x = int(g.left() + g.width() / 4.0)
    hot_x = int(g.left() + g.width() * 3.0 / 4.0)

    image = pane.grab().toImage()
    cold, hot = image.pixelColor(cold_x, mid_y), image.pixelColor(hot_x, mid_y)
    assert cold != PANEL and hot != PANEL, "the heatmap skipped out-of-band cells"
    assert cold.blue() > cold.red(), "the bottom of the scale is not cold"
    assert hot.red() > hot.blue(), "the top of the scale is not hot"

    # Border at full alpha with the heat off and nothing in band: no pixel
    # of the cell's outer ring may be painted. Entering the band paints it.
    view.heat_slider.setValue(0)
    ring_rows = range(int(g.top()) - 1, int(g.top()) + 3)
    image = pane.grab().toImage()
    assert all(image.pixelColor(cold_x, y) == PANEL for y in ring_rows), (
        "an out-of-band cell grew a border ring"
    )
    view.set_block_state(np.array([0.0, 10.0], np.float32), np.ones(2, bool), None)
    image = pane.grab().toImage()
    assert any(image.pixelColor(cold_x, y) != PANEL for y in ring_rows), (
        "the ring did not appear when the cell entered the band"
    )


def test_holding_shift_peeks_under_every_overlay(qtbot: QtBot) -> None:
    """Shift down hides the grid; shift up restores it — from anywhere, since
    the filter listens at the application rather than at one focus target."""
    view = StepCompositeView()
    qtbot.addWidget(view)
    view.set_grid_visible(True)
    view.show()

    def shift(kind: QEvent.Type) -> None:
        # Through sendEvent so the application-level filter runs, exactly as
        # it would for a real key press routed to any focused widget.
        event = QKeyEvent(kind, Qt.Key.Key_Shift, Qt.KeyboardModifier.ShiftModifier)
        QApplication.sendEvent(view.pane, event)

    assert not view.peeking
    shift(QEvent.Type.KeyPress)
    assert view.peeking
    shift(QEvent.Type.KeyRelease)
    assert not view.peeking
