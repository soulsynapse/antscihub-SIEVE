"""The step composite: selection targeting, the refresh guard, and the HUD.

Four claims, each a distinct way the composite could quietly wreck the tab.
A wrong target would compose frames of a step the user did not select; a
playhead refresh that ran while a window render was outstanding would
displace the graphs' render from the runner's one pending slot and the
series would never arrive; a refresh that cleared the HUD would erase
the window's cost series thirty times a second during playback; and a
pair that painted only at `render_finished` would leave the pane blank
for the whole first window render of every source.

`TestMagnifier` is a fifth: the overlay describes the pixels under it, so a
zoom that moved one layer and not the other would be worse than no zoom.
"""

from __future__ import annotations

from collections.abc import Iterator
from fractions import Fraction
from time import perf_counter
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QObject, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus, Recorder
from sieve.core.types import ROI
from sieve.gui.band_plot import PANEL
from sieve.gui.composite_view import GRID_STEPS, StepCompositeView
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import BAND_DRAG_BUDGET, FilterTab
from sieve.gui.transport.player import VideoPlayer
from tests.gui.qt_input import click, leave, move, wheel

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
    window_render_changed = Signal(bool)

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
def metrics() -> MetricBus:
    """The tab's bus, held by the test so a publication can be heard."""
    return MetricBus()


@pytest.fixture
def tab(
    qtbot: QtBot,
    player: VideoPlayer,
    document: ReplicateDocument,
    stub: _StubRunner,
    metrics: MetricBus,
) -> Iterator[FilterTab]:
    instance = FilterTab(player, document, stub, metrics=metrics)  # type: ignore[arg-type]
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


def test_playhead_refreshes_never_displace_each_other(
    tab: FilterTab, stub: _StubRunner, player: VideoPlayer
) -> None:
    """The same guard against itself, and the reason the pane ever went blank.

    A refresh is a single-frame render, and a single-frame render's only frame
    boundary is *before* its one delivery — so superseding one does not make it
    late, it makes it never arrive. Playback submits a refresh per playhead
    move, and on a chain whose frame costs more than a playback tick every
    render started was abandoned by the next move: the pane froze for the whole
    of playback while the graphs the last window render filled kept updating,
    and pausing (or smashing space) let one land.

    So a refresh may not be issued while one is outstanding, and the move that
    was suppressed is not lost — it is re-issued at the newest playhead when
    the outstanding one reports, which is what leaves the pane on the frame the
    user paused at.
    """
    stub.opened.emit()
    stub.render_finished.emit(object())  # the graphs' render is out of the way

    frame = QImage(160, 120, QImage.Format.Format_RGB32)
    player.frame_changed.emit(5, frame)
    assert stub.frame_renders == [5]

    player.frame_changed.emit(6, frame)
    player.frame_changed.emit(7, frame)
    assert stub.frame_renders == [5], "a refresh displaced the refresh still rendering"

    stub.render_finished.emit(object())
    assert stub.frame_renders == [5, 7], "the suppressed playhead was dropped rather than deferred"

    # And nothing is left armed: a report with no move behind it submits nothing.
    stub.render_finished.emit(object())
    assert stub.frame_renders == [5, 7]


def test_a_playhead_refresh_never_erases_the_series_or_the_final_derivation(
    qtbot: QtBot,
    tab: FilterTab,
    stub: _StubRunner,
    document: ReplicateDocument,
    player: VideoPlayer,
) -> None:
    """The refresh guard's other half — state, not slots.

    A composite refresh is issued through the runner like any render, so its
    `render_started` reached `_collector_start`, which restarted the collector
    and re-stamped the detector. Under playback the sequence was fatal every
    time: the window render finishes, the final derivation is submitted, the
    next playhead move starts a composite refresh — and the final result is
    dropped on arrival as stale while the series it came from is erased. The
    graphs filled and then silently never finished; a signal switch appeared
    to do nothing at all.

    The ordering is exact and single-threaded up to the wait: the refresh is
    issued before the event loop can deliver the detector's queued result, so
    without the guard the final pass is always assassinated.
    """
    document.bind_source(1000, 800, 40, Fraction(20))
    consumer = stub.consumers[-1]
    assert consumer is not None
    stub.render_started.emit(stub.revision)

    node_id = next(
        s.node.node_id
        for s in tab.chain.steps
        if s.node is not None and s.node.filter_id == "block_signal"
    )
    for index in range(3):
        consumer(  # type: ignore[operator]
            SimpleNamespace(
                index=index, outputs={node_id: SimpleNamespace(data=np.ones((2, 2), np.float32))}
            )
        )

    with qtbot.waitSignal(tab.graphs_updated, timeout=10_000):
        # `render_finished` submits the final derivation; the playhead move
        # right behind it issues the refresh before the result can arrive.
        stub.render_finished.emit(object())
        player.frame_changed.emit(1, QImage(160, 120, QImage.Format.Format_RGB32))
        assert stub.frame_renders == [1], "the refresh this test needs was never issued"

    assert not tab.summary_text.endswith(" · filling"), "the final pass never landed"


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


def test_rescale_cost_readout_waits_for_two_scales(
    tab: FilterTab,
    stub: _StubRunner,
    document: ReplicateDocument,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One completed scale is not enough; the second draws the fitted knee."""
    clock = 0.0
    monkeypatch.setattr("sieve.gui.filter_tab.perf_counter", lambda: clock)

    document.bind_source(1000, 800, 40, Fraction(20))
    first_revision = stub.revision
    stub.render_started.emit(first_revision)
    clock = 4.0
    stub.render_finished.emit(SimpleNamespace(frames=40, reuse=0.0))

    assert tab.rescale_cost_text == "cost: needs another scale"

    tab.downsample_knob.setValue(0.5)
    second_revision = stub.revision
    clock = 10.0
    stub.render_started.emit(second_revision)
    clock = 11.75
    stub.render_finished.emit(SimpleNamespace(frames=40, reuse=0.0))

    # Two scales fit exactly, so the projection is marked as an estimate.
    assert tab.rescale_cost_text == "cost ~43.7 ms/fr; knee 0.58"


def test_a_warm_render_does_not_join_a_cold_one_in_the_rescale_fit(
    tab: FilterTab,
    stub: _StubRunner,
    document: ReplicateDocument,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The second scale reused the prefix, so its wall time skipped the decode."""
    clock = 0.0
    monkeypatch.setattr("sieve.gui.filter_tab.perf_counter", lambda: clock)

    document.bind_source(1000, 800, 40, Fraction(20))
    stub.render_started.emit(stub.revision)
    clock = 4.0
    stub.render_finished.emit(SimpleNamespace(frames=40, reuse=0.0))

    tab.downsample_knob.setValue(0.5)
    clock = 10.0
    stub.render_started.emit(stub.revision)
    clock = 11.75
    stub.render_finished.emit(SimpleNamespace(frames=40, reuse=0.8))

    assert tab.rescale_cost_text == "cost: cache reuse differs between scales"


def test_a_first_step_targets_base_is_the_replicates_crop(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument, player: VideoPlayer
) -> None:
    """The overlay says *where inside the replicate*, so the frame under it
    must be the replicate's crop, not the parent footage the graph never saw.

    The one composite base that comes from the player rather than the render
    is the first step's input, and the ROI is in source pixels (1000x800
    here) while the player frame may be a half-size proxy — so the crop must
    scale by the image's actual size. Scale 0.5, not the default: an identity
    rescale's base is the render's own output (the no-op path is bit-exact),
    and only a first step that really transforms falls back to the player.
    """
    card = tab.stack.card_for("rescale")
    assert card is not None
    card.mousePressEvent(None)
    tab.downsample_knob.setValue(0.5)

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


def test_an_identity_rescale_first_steps_base_is_its_own_output(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument, player: VideoPlayer
) -> None:
    """At scale 1.0 the rescale output is bit-identical to its input
    (`rescale_cpu`'s no-op path), so the render's own frame is the honest
    base. The player fallback is a scrub proxy: blending a proxy under a
    full-resolution output painted a quality difference the graph does not
    have — the input·output slider at 0% degraded a downsample-1.0 chain.
    """
    card = tab.stack.card_for("rescale")
    assert card is not None
    card.mousePressEvent(None)

    document.add_roi(ROI(x=200, y=100, width=300, height=200))
    document.select(0)
    stub.render_finished.emit(object())
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
    assert (base.width(), base.height()) == (8, 8), "the base is not the render's own output"


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


def _grid_view(qtbot: QtBot, ny: int, nx: int, size: tuple[int, int]) -> StepCompositeView:
    view = StepCompositeView()
    qtbot.addWidget(view)
    view.resize(*size)
    view.set_grid_visible(True)
    view.set_grid(ny, nx)
    view.set_block_state(np.zeros(ny * nx, np.float32), np.zeros(ny * nx, bool), None)
    view.show()
    return view


def test_two_adjacent_detected_cells_share_one_one_pixel_wall(qtbot: QtBot) -> None:
    """The wall between two detected cells is 1 px, not 2.

    Each cell used to stroke its own ring, so neighbouring detected cells laid
    their rings side by side: 2 px inside a detected region and 1 px on its
    outer boundary, which is backwards — the interior lines carry the least
    information and got the heaviest ink. Measured with the border at zero and
    the fill opaque, so the wall reads as bare panel and its width is a count
    of background pixels: exactly one, where it used to be two.
    """
    view = _grid_view(qtbot, 1, 2, (400, 240))
    view.set_block_state(np.zeros(2, np.float32), np.ones(2, bool), None)
    view.fill_slider.setValue(GRID_STEPS)
    view.line_slider.setValue(0)
    view.heat_slider.setValue(0)

    pane = view.pane
    xs, ys = pane.grid_edges()
    row_y = (ys[0] + ys[1]) // 2
    image = pane.grab().toImage()

    bare = [x for x in range(xs[1] - 5, xs[1] + 6) if image.pixelColor(x, row_y) == PANEL]
    assert bare == [xs[1]], f"the shared wall is {len(bare)} px wide, not 1"


def test_a_lone_detected_cell_still_shows_a_closed_ring(qtbot: QtBot) -> None:
    """The other side of the shared-wall rule.

    Giving the bottom and right pixel lines to a detected neighbour is only
    sound if a cell with no detected neighbour keeps them: a lone in-band cell
    must be ringed on all four sides, one pixel thick, with bare heat inside
    it at fill 0 and bare panel outside.
    """
    view = _grid_view(qtbot, 3, 3, (400, 400))
    in_band = np.zeros(9, bool)
    in_band[4] = True
    view.set_block_state(np.zeros(9, np.float32), in_band, None)
    view.line_slider.setValue(GRID_STEPS)
    view.fill_slider.setValue(0)
    view.heat_slider.setValue(0)

    pane = view.pane
    xs, ys = pane.grid_edges()
    x0, x1, y0, y1 = xs[1], xs[2] - 1, ys[1], ys[2] - 1
    image = pane.grab().toImage()

    for y in range(y0, y1 + 1):
        assert image.pixelColor(x0, y) != PANEL, f"the left wall breaks at y={y}"
        assert image.pixelColor(x1, y) != PANEL, f"the right wall breaks at y={y}"
    for x in range(x0, x1 + 1):
        assert image.pixelColor(x, y0) != PANEL, f"the top wall breaks at x={x}"
        assert image.pixelColor(x, y1) != PANEL, f"the bottom wall breaks at x={x}"
    mid_y = (y0 + y1) // 2
    assert image.pixelColor(x0 - 1, mid_y) == PANEL, "the ring bled outside the cell"
    assert image.pixelColor(x0 + 1, mid_y) == PANEL, "the ring is more than 1 px thick"
    assert image.pixelColor(x1 + 1, mid_y) == PANEL, "the ring bled into the next cell"


def test_the_heatmap_tiles_with_no_uncovered_row_at_any_pane_height(qtbot: QtBot) -> None:
    """The seam: a 1 px line of unblended footage across the heatmap.

    Each cell used to derive its own origin and extent from a float cell size,
    so `left + i*w` and `left + (i-1)*w + w` — the same real number — could
    land either side of a half pixel and the fills rounded apart. It showed up
    at *particular* pane heights only, which is why the height is swept rather
    than sampled: one geometry proves nothing about the arithmetic.
    """
    view = _grid_view(qtbot, 12, 3, (300, 200))
    view.set_block_state(np.full(36, 5.0, np.float32), np.zeros(36, bool), None)
    view.set_scale_max(10.0)
    view.heat_slider.setValue(GRID_STEPS)
    view.fill_slider.setValue(0)
    view.line_slider.setValue(0)

    pane = view.pane
    for height in range(200, 260):
        view.resize(300, height)
        QApplication.processEvents()
        rect = pane.grid_rect()
        column = int(rect.center().x())
        image = pane.grab().toImage()
        gaps = [
            y
            for y in range(int(rect.top()) + 1, int(rect.bottom()) - 1)
            if image.pixelColor(column, y) == PANEL
        ]
        assert not gaps, f"unblended row(s) {gaps} through the heatmap at height {height}"


def test_the_heat_layer_registers_with_the_grid_while_magnified(qtbot: QtBot) -> None:
    """The heat image is built from the cells the *fit* can show, not all of them.

    Magnified, the grid runs off under the letterbox, and the layer skips the
    cells out there rather than expanding a picture the clip throws away. That
    makes the first drawn cell an index into the grid rather than cell zero,
    and an off-by-one there shifts every colour one cell sideways — a heatmap
    that describes the neighbour of the pixels under it, which no state test
    can see. Cold left, hot right: the boundary between them must still be the
    grid line the ring layer reads.
    """
    view = _grid_view(qtbot, 1, 2, (400, 220))
    view.set_scale_max(10.0)
    view.set_block_state(np.array([0.0, 10.0], np.float32), np.zeros(2, bool), None)
    view.heat_slider.setValue(GRID_STEPS)
    view.fill_slider.setValue(0)
    view.line_slider.setValue(0)

    pane = view.pane
    wheel(pane, pane.grid_rect().center(), 3)
    QApplication.processEvents()
    assert pane.magnifier.magnified, "the wheel did not magnify"

    xs, ys = pane.grid_edges()
    row_y = (max(ys[0], 0) + min(ys[1], pane.height())) // 2
    image = pane.grab().toImage()
    left, right = image.pixelColor(xs[1] - 1, row_y), image.pixelColor(xs[1], row_y)
    assert left.blue() > left.red(), "the last pixel of the cold cell is not cold"
    assert right.red() > right.blue(), "the first pixel of the hot cell is not hot"


def test_a_grid_larger_than_the_playhead_row_leaves_its_tail_unpainted(qtbot: QtBot) -> None:
    """Rule 6: a cell with no value must not be coloured as if it had one.

    The grid shape and the block row arrive from different calls, so a row can
    be short of the shape for a repaint — and the heat layer covers every cell
    unconditionally, which is exactly where a missing value would be rendered
    as the bottom of the scale (cold, and indistinguishable from a real cold
    cell) if the tail were not left bare.
    """
    view = _grid_view(qtbot, 2, 2, (400, 400))
    view.set_scale_max(10.0)
    view.set_block_state(np.full(3, 10.0, np.float32), np.zeros(3, bool), None)
    view.heat_slider.setValue(GRID_STEPS)

    pane = view.pane
    xs, ys = pane.grid_edges()
    image = pane.grab().toImage()
    painted = image.pixelColor((xs[0] + xs[1]) // 2, (ys[0] + ys[1]) // 2)
    tail = image.pixelColor((xs[1] + xs[2]) // 2, (ys[1] + ys[2]) // 2)
    assert painted != PANEL, "the cells that do have a value went unpainted"
    assert tail == PANEL, "a cell with no value was coloured"


def test_the_heat_layer_costs_pixels_not_blocks(qtbot: QtBot) -> None:
    """The layer is drawn once, not once per cell.

    Not a budget — no ceiling in `bench/budgets.py` covers a repaint, and a
    wall-clock number here would only measure this machine. The claim is the
    *shape* of the cost: the heat layer covers the same pane whatever the grid
    is, so 256 times the cells must not cost 256 times the paint. A `QColor`
    and a `fillRect` per cell made it 34 ms at the reference B = 16,384 and the
    pane repainted per frame and per hover crossing, which is the lag this
    pins. Min of five, because the floor of a repeated measurement is the one
    statistic a loaded machine cannot inflate.
    """
    view = _grid_view(qtbot, 8, 8, (400, 400))
    view.set_scale_max(10.0)
    view.heat_slider.setValue(GRID_STEPS)
    view.fill_slider.setValue(0)
    view.line_slider.setValue(0)
    pane = view.pane

    def paint_ms(cells: int) -> float:
        view.set_grid(cells, cells)
        view.set_block_state(
            np.full(cells * cells, 5.0, np.float32), np.zeros(cells * cells, bool), None
        )
        QApplication.processEvents()
        samples: list[float] = []
        for _ in range(5):
            started = perf_counter()
            pane.grab()
            samples.append((perf_counter() - started) * 1000.0)
        return min(samples)

    small, large = paint_ms(16), paint_ms(256)
    assert large < small * 5.0 + 5.0, (
        f"256x more cells cost {large:.1f} ms against {small:.1f} ms — "
        "the layer is being drawn per cell again"
    )


class TestMagnifier:
    """The wheel over the pane, and the mapping it moves under.

    At a realistic block count a cell is a few screen pixels, so the grid is
    only readable magnified — which makes the *mapping* the whole feature: a
    view that zooms while the overlay or the hit test stays behind is worse
    than no zoom at all.
    """

    def test_the_block_under_the_cursor_stays_under_the_cursor(self, qtbot: QtBot) -> None:
        """The item's first claim, and the reason the geometry lands first.

        The anchor's placement is the whole test and it took two tries. A
        magnifier that zoomed and never panned still holds the *centre* cell
        under the cursor, and it holds a mid-cell anchor too: with no pan a
        point at fraction u drifts to 0.5 + (u - 0.5)/zoom, which is a drift
        toward the centre of a quarter of the grid at most. So the anchor sits
        just inside a cell boundary, a hair short of 0.25 — near enough that
        the drift crosses it in both axes and the unpanned magnifier answers
        with the diagonal neighbour instead. The second assertion is what makes
        the first mean anything: the map really moved under the cursor, rather
        than the wheel having done nothing at all.
        """
        # The view is held, not just its pane: dropping the last Python
        # reference to the parent lets Qt delete the child out from under the
        # test, which shows up only under the full suite's collection timing.
        view = _grid_view(qtbot, 4, 4, (400, 400))
        pane = view.pane
        fit = pane.grid_rect()
        anchor = QPointF(fit.left() + fit.width() * 0.24, fit.top() + fit.height() * 0.24)
        elsewhere = QPointF(fit.left() + fit.width() * 0.8, fit.top() + fit.height() * 0.8)

        before, before_elsewhere = pane.block_at(anchor), pane.block_at(elsewhere)
        wheel(pane, anchor, 4)

        assert pane.magnifier.zoom > 1.0
        assert pane.block_at(anchor) == before
        assert pane.block_at(elsewhere) != before_elsewhere, "the map did not move at all"

    def test_scrolling_out_never_zooms_past_the_fit(self, qtbot: QtBot) -> None:
        """The floor, and it holds *during* the storm rather than only after it.

        Exact equality with the pre-zoom rect, not approximate: a floor
        implemented by clamping a running product lands a float epsilon under
        the fit and leaves a hairline of panel inside the picture, which is a
        visible symptom nobody traces back to arithmetic.

        Both wheels are off-centre, and that is not decoration. Zoomed and
        panned about the pane's own centre, the covering rect and the
        *unclamped* one are the same numbers — so a storm at the centre
        exercises the arithmetic and never the clamp, and passes with the
        clamp deleted. Away from the centre they diverge, and a corner is
        where a pan that pulls content off the edge shows up as bare panel
        inside the picture.
        """
        view = _grid_view(qtbot, 3, 4, (400, 300))
        pane = view.pane
        fit = pane.grid_rect()
        corner = QPointF(fit.left() + fit.width() * 0.15, fit.top() + fit.height() * 0.85)

        wheel(pane, QPointF(fit.left() + fit.width() * 0.8, fit.center().y()), 4)
        for _ in range(40):
            wheel(pane, corner, -1)
            assert pane.grid_rect().width() >= fit.width()
            assert pane.grid_rect().height() >= fit.height()
            assert pane.grid_rect().contains(fit), "a pan opened a gap inside the picture"

        assert view.zoom == 1.0
        assert pane.grid_rect() == fit

    def test_the_grid_stays_registered_to_the_image_at_every_zoom(self, qtbot: QtBot) -> None:
        """Pixels, not rectangles: the overlay describes the picture under it.

        A base image split black | red under a 1x2 grid whose right cell is
        filled opaque. Registered, the fill's edge lands exactly on the image's
        seam: black to its left, `ACCENT` to its right, and bare red nowhere
        but the fill's own one-pixel inset. Red rather than green because
        `ACCENT`, the fill's own colour, is a green.

        Both directions are checked, because either alone is passed by a
        drift the other way. A grid still drawn against the un-zoomed content
        rect — what this widget did before the magnifier — leaves a band of
        bare red where the image seam moved left of the cell seam, and a band
        of fill over black where it moved right; one of those bands is invisible
        to a red-only test, and which one depends on nothing but the sign of
        the pan.

        The anchor is off-centre for the same reason: the fit and the magnified
        rect share a centre when the pan is centred, so a centred zoom would
        leave a drifting grid's seam sitting exactly on the image's.
        """
        view = _grid_view(qtbot, 1, 2, (400, 240))
        view.set_block_state(np.zeros(2, np.float32), np.array([False, True]), None)
        view.fill_slider.setValue(GRID_STEPS)  # opaque, so the fill hides the image
        view.line_slider.setValue(0)
        view.heat_slider.setValue(0)

        image = QImage(80, 40, QImage.Format.Format_RGB32)
        image.fill(QColor(0, 0, 0))
        for x in range(40, 80):
            for y in range(40):
                image.setPixelColor(x, y, QColor(220, 0, 0))
        view.set_frames(image, None)

        pane = view.pane
        fit = pane.grid_rect()
        anchor = QPointF(fit.left() + fit.width() * 0.7, fit.center().y())
        row = int(fit.center().y())
        strip = range(int(fit.left()) + 2, int(fit.right()) - 2)

        # Qt interpolates the base image, so the seam itself is a blend band
        # a magnified source pixel wide; registration is a claim about
        # everywhere else, so that band is excluded rather than tolerated.
        band = 12

        for _ in range(4):
            grabbed = pane.grab().toImage()
            zoom = pane.magnifier.zoom
            # Where the picture's own seam is, read off the rect the image was
            # drawn into — the grid is what has to agree with it.
            seam = pane.view_rect().center().x()
            assert fit.left() + band < seam < fit.right() - band, "the seam left the strip"

            bare = [
                x for x in strip if abs(x - seam) > band and grabbed.pixelColor(x, row).red() > 150
            ]
            assert not bare, f"{len(bare)} px of unfilled red at {zoom:.2f}x"
            assert grabbed.pixelColor(int(seam + band), row).green() > 150, (
                f"the fill does not reach the image seam at {zoom:.2f}x"
            )
            assert grabbed.pixelColor(int(seam - band), row).green() < 60, (
                f"the fill spilled past the image seam at {zoom:.2f}x"
            )
            wheel(pane, anchor, 1)

    def test_a_click_in_the_letterbox_hits_no_block(self, qtbot: QtBot) -> None:
        """The second containment test in `block_at`.

        A magnified grid runs off under the letterbox, where it is clipped
        away at paint time. A hit test that read the grid rect alone would
        solo a cell from a strip of bare panel — rule 6's mirror direction, a
        control answering where nothing is drawn.
        """
        view = _grid_view(qtbot, 1, 2, (400, 400))
        pane = view.pane
        fit = pane.grid_rect()
        letterbox = QPointF(fit.center().x(), fit.top() - 20.0)
        assert letterbox.y() > 0.0, "the fixture has no letterbox to click in"

        wheel(pane, QPointF(fit.center()), 6)

        assert pane.grid_rect().contains(letterbox), "the fixture no longer covers the letterbox"
        assert pane.block_at(letterbox) is None


def test_soloing_repaints_and_never_re_derives(
    tab: FilterTab, metrics: MetricBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What makes the gesture affordable at pointer speed.

    `recompute` does not read `solo_block` (pinned in
    `tests/unit/test_chain_model.py`), so a solo that went through the cheap
    *derive* tier paid an in-band count and a windowed mean over the whole
    series to produce a bit-identical update. One click per block could
    afford that; one crossing per pointer move cannot. Counted rather than
    timed — the claim is that the work does not happen, not that it is fast.

    The band drag is asserted alongside because it is the regression this
    could cause: a solo skipping the derivation must not take the drag with it.
    """
    recorder = Recorder()
    metrics.subscribe(recorder.record)
    derives: list[bool] = []

    def counting(*, reuse_band_power: bool) -> None:
        derives.append(reuse_band_power)

    monkeypatch.setattr(tab, "_derive", counting)

    tab._on_solo(2)  # pyright: ignore[reportPrivateUsage]
    assert tab.chain.detector.solo_block == 2
    assert derives == []
    assert len(recorder.samples(BAND_DRAG_BUDGET)) == 1, "the gesture publishes nothing to miss"

    tab._on_solo(2)  # pyright: ignore[reportPrivateUsage]
    assert len(recorder.samples(BAND_DRAG_BUDGET)) == 1, "an unchanged solo repainted anyway"

    tab._on_value_drag(0.1, 0.9)  # pyright: ignore[reportPrivateUsage]
    assert derives == [True]


class _SoloModel:
    """The state model the pane is talking to, small enough to read.

    The pane emits and never applies, so a test that only listened would drive
    a pane whose own `solo` never moved — and the pane compares against exactly
    that value to decide whether a crossing is worth asking about. Applying
    what is asked for is therefore not decoration: it is the half of the loop
    the deduplication reads.
    """

    def __init__(self, view: StepCompositeView, blocks: int) -> None:
        self._view = view
        self._blocks = blocks
        self.asked: list[object] = []
        view.solo_toggled.connect(self.apply)

    def apply(self, block: object) -> None:
        self.asked.append(block)
        solo = block if isinstance(block, int) else None
        self._view.set_block_state(
            np.zeros(self._blocks, np.float32), np.zeros(self._blocks, bool), solo
        )


def _cell(view: StepCompositeView, block: int) -> QPointF:
    """The centre of a block, in the pane's coordinates."""
    pane = view.pane
    rect = pane.grid_rect()
    ny, nx = pane.grid
    row, col = divmod(block, nx)
    return QPointF(
        rect.left() + rect.width() * (col + 0.5) / nx,
        rect.top() + rect.height() * (row + 0.5) / ny,
    )


class TestHoverSolosAndClickPins:
    """The two tiers of the solo gesture.

    Soloing exists to put one block's trace on the density plot, which is not
    the grid — so a rule where solo is strictly the block under the pointer
    clears at the instant the user looks at what they asked for. Hence: hover
    previews, a click pins, and leaving the grid reverts to the pin.
    """

    def test_hovering_across_blocks_solos_each_in_turn_without_a_click(self, qtbot: QtBot) -> None:
        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)
        hovered: list[object] = []
        view.pane.hover_changed.connect(hovered.append)

        for block in (0, 5, 10):
            move(view.pane, _cell(view, block))

        assert model.asked == [0, 5, 10]
        assert view.pane.solo == 10
        # The footer readout is driven by the same crossing and is unchanged
        # by solo having joined it — one signal, two consumers, still.
        assert hovered == [0, 5, 10]

    def test_a_pin_survives_leaving_and_hover_still_previews_over_it(self, qtbot: QtBot) -> None:
        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)

        move(view.pane, _cell(view, 5))
        click(view.pane, _cell(view, 5))  # pinned; hover already solos it, so nothing is asked
        move(view.pane, _cell(view, 9))  # a pin does not stop the preview
        leave(view.pane)

        assert model.asked == [5, 9, 5]
        assert view.pane.solo == 5

    def test_leaving_with_nothing_pinned_clears_the_solo(self, qtbot: QtBot) -> None:
        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)

        move(view.pane, _cell(view, 3))
        leave(view.pane)

        assert model.asked == [3, None]
        assert view.pane.solo is None

    def test_a_second_click_unpins_so_leaving_clears_again(self, qtbot: QtBot) -> None:
        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)

        move(view.pane, _cell(view, 2))
        click(view.pane, _cell(view, 2))
        click(view.pane, _cell(view, 2))
        leave(view.pane)

        # Neither click asks for anything: hover is soloing the block either
        # way, and what the click changed is what leaving reverts to.
        assert model.asked == [2, None]
        assert view.pane.latched is None

    def test_the_grid_going_away_drops_the_pin(self, qtbot: QtBot) -> None:
        """Rule 6's mirror direction: a pin outliving the grid keeps a block
        soloed in the density plot with nothing on screen saying which."""
        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)

        move(view.pane, _cell(view, 7))
        click(view.pane, _cell(view, 7))
        view.set_grid_visible(False)

        assert model.asked == [7, None]
        assert view.pane.latched is None


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
