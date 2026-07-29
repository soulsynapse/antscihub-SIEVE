














from __future__ import annotations

from collections.abc import Iterator
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
from sieve.gui.player import VideoPlayer
from tests.gui.qt_input import click, leave, move, wheel

pytestmark = pytest.mark.gui


class _StubRunner(QObject):







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

    return MetricBus()


@pytest.fixture
def tab(
    qtbot: QtBot,
    player: VideoPlayer,
    document: ReplicateDocument,
    stub: _StubRunner,
    metrics: MetricBus,
) -> Iterator[FilterTab]:
    instance = FilterTab(player, document, stub, metrics=metrics)
    qtbot.addWidget(instance)
    yield instance




    instance.shutdown()


def test_selection_defaults_to_the_tail_and_targets_the_deepest_rendered_step(
    tab: FilterTab,
) -> None:








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








    stub.opened.emit()
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















    stub.opened.emit()
    stub.render_finished.emit(object())

    frame = QImage(160, 120, QImage.Format.Format_RGB32)
    player.frame_changed.emit(5, frame)
    assert stub.frame_renders == [5]

    player.frame_changed.emit(6, frame)
    player.frame_changed.emit(7, frame)
    assert stub.frame_renders == [5], "a refresh displaced the refresh still rendering"

    stub.render_finished.emit(object())
    assert stub.frame_renders == [5, 7], "the suppressed playhead was dropped rather than deferred"


    stub.render_finished.emit(object())
    assert stub.frame_renders == [5, 7]


def test_a_playhead_refresh_never_erases_the_series_or_the_final_derivation(
    qtbot: QtBot,
    tab: FilterTab,
    stub: _StubRunner,
    document: ReplicateDocument,
    player: VideoPlayer,
) -> None:















    document.bind_source(1000, 800, 40, 20.0)
    consumer = stub.consumers[-1]
    assert consumer is not None
    stub.render_started.emit(stub.revision)

    node_id = next(
        s.node.node_id
        for s in tab.chain.steps
        if s.node is not None and s.node.filter_id == "block_signal"
    )
    for index in range(3):
        consumer(
            SimpleNamespace(
                index=index, outputs={node_id: SimpleNamespace(data=np.ones((2, 2), np.float32))}
            )
        )

    with qtbot.waitSignal(tab.graphs_updated, timeout=10_000):


        stub.render_finished.emit(object())
        player.frame_changed.emit(1, QImage(160, 120, QImage.Format.Format_RGB32))
        assert stub.frame_renders == [1], "the refresh this test needs was never issued"

    assert not tab.summary_text.endswith(" · filling"), "the final pass never landed"


def test_the_pair_paints_at_the_playhead_frame_not_at_render_finished(
    tab: FilterTab, stub: _StubRunner
) -> None:








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
    consumer(SimpleNamespace(index=0, outputs=outputs))
    assert tab.composite.frames() == (None, None), "painted before the GUI thread heard"

    stub.frame_cost.emit(0, 5.0)
    base, over = tab.composite.frames()
    assert base is not None, "the pair waited for render_finished"


    assert over is None
    assert tab.composite.pane.grid_on


def test_a_composite_refresh_leaves_the_hud_series_alone(
    tab: FilterTab, stub: _StubRunner, player: VideoPlayer
) -> None:














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










    card = tab.stack.card_for("rescale")
    assert card is not None
    card.mousePressEvent(None)
    tab.downsample_knob.setValue(0.5)

    document.add_roi(ROI(x=200, y=100, width=300, height=200))
    document.select(0)
    stub.render_finished.emit(object())
    player.frame_changed.emit(3, QImage(500, 400, QImage.Format.Format_RGB32))

    grab = stub.frame_consumers[-1]
    assert grab is not None
    node = next(s.node for s in tab.chain.steps if s.step_id == "rescale")
    assert node is not None
    outputs = {node.node_id: SimpleNamespace(data=np.full((8, 8), 100, np.uint8))}
    grab(SimpleNamespace(index=3, outputs=outputs))
    stub.frame_cost.emit(3, 0.1)

    base, _ = tab.composite.frames()
    assert base is not None
    assert (base.width(), base.height()) == (150, 100), "the crop ignored the proxy scale"


def test_an_identity_rescale_first_steps_base_is_its_own_output(
    tab: FilterTab, stub: _StubRunner, document: ReplicateDocument, player: VideoPlayer
) -> None:






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
    grab(SimpleNamespace(index=3, outputs=outputs))
    stub.frame_cost.emit(3, 0.1)

    base, _ = tab.composite.frames()
    assert base is not None
    assert (base.width(), base.height()) == (8, 8), "the base is not the render's own output"


def test_border_alpha_zero_separates_blocks_and_equal_alphas_read_as_a_mass(
    qtbot: QtBot,
) -> None:









    view = StepCompositeView()
    qtbot.addWidget(view)
    view.resize(400, 400)
    view.set_grid_visible(True)
    view.set_grid(2, 2)
    view.set_block_state(np.full(4, 5.0, np.float32), np.ones(4, bool), None)
    view.fill_slider.setValue(GRID_STEPS)
    view.line_slider.setValue(0)
    view.heat_slider.setValue(0)
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

    view.line_slider.setValue(GRID_STEPS)
    image = pane.grab().toImage()
    assert all(image.pixelColor(x, row_y) != PANEL for x in strip), (
        "bare background survived equal alphas — the mass has seams"
    )


def test_the_heatmap_runs_cold_to_hot_and_borders_mark_only_detected_cells(
    qtbot: QtBot,
) -> None:







    view = StepCompositeView()
    qtbot.addWidget(view)
    view.resize(400, 220)
    view.set_grid_visible(True)
    view.set_grid(1, 2)
    view.set_scale_max(10.0)

    view.set_block_state(np.array([0.0, 10.0], np.float32), np.zeros(2, bool), None)
    view.heat_slider.setValue(GRID_STEPS)
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


class TestMagnifier:








    def test_the_block_under_the_cursor_stays_under_the_cursor(self, qtbot: QtBot) -> None:
















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




















        view = _grid_view(qtbot, 1, 2, (400, 240))
        view.set_block_state(np.zeros(2, np.float32), np.array([False, True]), None)
        view.fill_slider.setValue(GRID_STEPS)
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




        band = 12

        for _ in range(4):
            grabbed = pane.grab().toImage()
            zoom = pane.magnifier.zoom


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












    recorder = Recorder()
    metrics.subscribe(recorder.record)
    derives: list[bool] = []

    def counting(*, reuse_band_power: bool) -> None:
        derives.append(reuse_band_power)

    monkeypatch.setattr(tab, "_derive", counting)

    tab._on_solo(2)
    assert tab.chain.detector.solo_block == 2
    assert derives == []
    assert len(recorder.samples(BAND_DRAG_BUDGET)) == 1, "the gesture publishes nothing to miss"

    tab._on_solo(2)
    assert len(recorder.samples(BAND_DRAG_BUDGET)) == 1, "an unchanged solo repainted anyway"

    tab._on_value_drag(0.1, 0.9)
    assert derives == [True]


class _SoloModel:









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

    pane = view.pane
    rect = pane.grid_rect()
    ny, nx = pane.grid
    row, col = divmod(block, nx)
    return QPointF(
        rect.left() + rect.width() * (col + 0.5) / nx,
        rect.top() + rect.height() * (row + 0.5) / ny,
    )


class TestHoverSolosAndClickPins:








    def test_hovering_across_blocks_solos_each_in_turn_without_a_click(self, qtbot: QtBot) -> None:
        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)
        hovered: list[object] = []
        view.pane.hover_changed.connect(hovered.append)

        for block in (0, 5, 10):
            move(view.pane, _cell(view, block))

        assert model.asked == [0, 5, 10]
        assert view.pane.solo == 10


        assert hovered == [0, 5, 10]

    def test_a_pin_survives_leaving_and_hover_still_previews_over_it(self, qtbot: QtBot) -> None:
        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)

        move(view.pane, _cell(view, 5))
        click(view.pane, _cell(view, 5))
        move(view.pane, _cell(view, 9))
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



        assert model.asked == [2, None]
        assert view.pane.latched is None

    def test_the_grid_going_away_drops_the_pin(self, qtbot: QtBot) -> None:


        view = _grid_view(qtbot, 4, 4, (400, 400))
        model = _SoloModel(view, 16)

        move(view.pane, _cell(view, 7))
        click(view.pane, _cell(view, 7))
        view.set_grid_visible(False)

        assert model.asked == [7, None]
        assert view.pane.latched is None


def test_holding_shift_peeks_under_every_overlay(qtbot: QtBot) -> None:


    view = StepCompositeView()
    qtbot.addWidget(view)
    view.set_grid_visible(True)
    view.show()

    def shift(kind: QEvent.Type) -> None:


        event = QKeyEvent(kind, Qt.Key.Key_Shift, Qt.KeyboardModifier.ShiftModifier)
        QApplication.sendEvent(view.pane, event)

    assert not view.peeking
    shift(QEvent.Type.KeyPress)
    assert view.peeking
    shift(QEvent.Type.KeyRelease)
    assert not view.peeking
