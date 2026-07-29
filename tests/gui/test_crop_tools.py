















from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLabel, QPushButton, QRadioButton, QSpinBox
from pytestqt.qtbot import QtBot

from sieve.core.types import ROI, VideoMetadata
from sieve.gui.crop_tools import CropToolsPanel
from sieve.gui.document import ReplicateDocument
from sieve.gui.player import VideoPlayer
from sieve.gui.replicate_tab import ReplicateTab
from sieve.gui.video_view import CropMode, VideoView
from tests.gui.qt_input import click, drag, move, press, release, wheel

pytestmark = pytest.mark.gui

WIDGET_SIZE = (800, 600)
INSET_X = 25.0
SCALE = 0.75

BOX = ROI(x=100, y=100, width=200, height=200)

SOURCE = VideoMetadata(path=Path("rack.mp4"), width=1000, height=800, fps=30.0, frame_count=1000)


def _widget_point(source_x: float, source_y: float) -> QPointF:

    return QPointF(INSET_X + source_x * SCALE, source_y * SCALE)


@pytest.fixture
def player(qapp: object) -> Iterator[VideoPlayer]:
    del qapp
    instance = VideoPlayer()
    yield instance
    instance.shutdown()


@pytest.fixture
def tab(qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument) -> ReplicateTab:

    instance = ReplicateTab(player, document)
    qtbot.addWidget(instance)
    player.opened.emit(SOURCE)
    view = instance.findChild(VideoView)
    assert view is not None
    view.resize(*WIDGET_SIZE)
    document.add_roi(BOX)
    return instance


@pytest.fixture
def view(tab: ReplicateTab) -> VideoView:
    found = tab.findChild(VideoView)
    assert found is not None
    return found


@pytest.fixture
def panel(tab: ReplicateTab) -> CropToolsPanel:
    return tab.tools_panel


def _field(panel: CropToolsPanel, name: str) -> QSpinBox:
    found = panel.findChild(QSpinBox, name)
    assert found is not None, f"no field named {name}"
    return found


def _toggle(panel: CropToolsPanel, name: str) -> QRadioButton:
    found = panel.findChild(QRadioButton, name)
    assert found is not None, f"no toggle named {name}"
    return found


def _button(panel: CropToolsPanel, name: str) -> QPushButton:
    found = panel.findChild(QPushButton, name)
    assert found is not None, f"no button named {name}"
    return found


def _centre(roi: ROI) -> tuple[float, float]:
    return (roi.x + roi.width / 2, roi.y + roi.height / 2)


def slow_drag(view: VideoView, start: QPointF, *waypoints: QPointF) -> None:









    press(view, start)
    for waypoint in waypoints:
        move(view, waypoint)
    release(view, waypoints[-1] if waypoints else start)


class TestUndoGranularity:


    WAYPOINTS = (
        _widget_point(220, 210),
        _widget_point(250, 220),
        _widget_point(280, 240),
        _widget_point(300, 250),
    )

    def test_one_drag_is_one_undo_step(self, view: VideoView, document: ReplicateDocument) -> None:






        before = document.undo_stack.count()

        slow_drag(view, _widget_point(200, 200), *self.WAYPOINTS)

        assert document.at(0).roi != BOX, "the drag did not move anything"
        assert document.undo_stack.count() == before + 1

    def test_undo_returns_the_box_to_where_the_drag_began(
        self, view: VideoView, document: ReplicateDocument
    ) -> None:







        slow_drag(view, _widget_point(200, 200), *self.WAYPOINTS)
        assert document.at(0).roi != BOX

        document.undo_stack.undo()

        assert document.at(0).roi == BOX

    def test_two_drags_are_two_undo_steps(
        self, view: VideoView, document: ReplicateDocument
    ) -> None:






        before = document.undo_stack.count()

        slow_drag(view, _widget_point(200, 200), *self.WAYPOINTS)
        slow_drag(view, _widget_point(300, 250), _widget_point(330, 270), _widget_point(350, 300))

        assert document.undo_stack.count() == before + 2

    def test_a_typed_dimension_is_its_own_undo_step(
        self, panel: CropToolsPanel, document: ReplicateDocument
    ) -> None:

        before = document.undo_stack.count()

        _field(panel, "roi-x").setValue(400)
        _field(panel, "roi-y").setValue(500)

        assert document.undo_stack.count() == before + 2
        assert document.at(0).roi == ROI(x=400, y=500, width=200, height=200)

    def test_an_abandoned_drag_leaves_no_trace(
        self, view: VideoView, document: ReplicateDocument
    ) -> None:





        press(view, _widget_point(200, 200))
        move(view, _widget_point(400, 350))
        view.keyPressEvent(
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        )

        assert document.at(0).roi == BOX


class TestToolsPanel:
    def test_the_fields_show_the_selected_replicate(self, panel: CropToolsPanel) -> None:
        for name, expected in (
            ("roi-x", BOX.x),
            ("roi-y", BOX.y),
            ("roi-width", BOX.width),
            ("roi-height", BOX.height),
        ):
            assert _field(panel, name).value() == expected

    def test_the_fields_follow_a_box_being_dragged(
        self, view: VideoView, panel: CropToolsPanel, document: ReplicateDocument
    ) -> None:





        drag(view, _widget_point(200, 200), _widget_point(300, 250))

        assert _field(panel, "roi-x").value() == document.at(0).roi.x == 200
        assert _field(panel, "roi-width").value() == BOX.width

    def test_a_drawn_region_fills_the_stamp_fields(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:

        drag(view, _widget_point(500, 400), _widget_point(637, 491))

        assert (_field(panel, "stamp-width").value(), _field(panel, "stamp-height").value()) == (
            137,
            91,
        )

    def test_typing_a_stamp_size_reaches_the_view(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:

        _field(panel, "stamp-width").setValue(137)
        _field(panel, "stamp-height").setValue(91)

        assert view.stamp_size == (137, 91)

    def test_a_typed_stamp_can_be_placed_without_drawing_one(
        self, view: VideoView, panel: CropToolsPanel, document: ReplicateDocument
    ) -> None:
        _field(panel, "stamp-width").setValue(137)
        _field(panel, "stamp-height").setValue(91)
        view.set_mode(CropMode.STAMP)

        click(view, _widget_point(700, 600))

        placed = document.at(len(document) - 1).roi
        assert (placed.width, placed.height) == (137, 91)

    def test_the_source_box_names_the_parent(self, panel: CropToolsPanel) -> None:

        label = panel.findChild(QLabel, "source-summary")
        assert label is not None
        text = label.text()
        assert "rack.mp4" in text
        assert "1000 x 800" in text
        assert "30.00 fps" in text

    def test_the_fit_button_returns_the_magnified_view(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:
        wheel(view, QPointF(400.0, 300.0), 4)
        assert view.zoom > 1.0

        panel.fit_requested.emit()

        assert view.zoom == 1.0



FIRST_DRAW = (_widget_point(500, 400), _widget_point(637, 491))


class TestStampByDefault:










    def test_a_completed_draw_puts_both_widgets_in_stamp_mode(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:







        assert view.mode is CropMode.DRAW

        drag(view, *FIRST_DRAW)

        assert view.mode is CropMode.STAMP
        assert _toggle(panel, "mode-stamp").isChecked()
        assert not _toggle(panel, "mode-draw").isChecked()

    def test_a_click_stamps_the_highlighted_replicate_not_the_last_drawn(
        self, view: VideoView, panel: CropToolsPanel, document: ReplicateDocument
    ) -> None:









        drag(view, *FIRST_DRAW)
        assert (document.at(1).roi.width, document.at(1).roi.height) == (137, 91)





        assert view.stamp_size == (137, 91)

        document.select(0)
        click(view, _widget_point(800, 700))

        placed = document.at(len(document) - 1).roi
        assert (placed.width, placed.height) == (BOX.width, BOX.height)
        assert _field(panel, "stamp-width").value() == BOX.width
        assert _field(panel, "stamp-height").value() == BOX.height

    def test_a_drag_in_stamp_mode_still_draws(
        self, view: VideoView, document: ReplicateDocument
    ) -> None:






        drag(view, *FIRST_DRAW)
        assert view.mode is CropMode.STAMP
        before = len(document)

        drag(view, _widget_point(700, 600), _widget_point(900, 750))

        assert len(document) == before + 1
        drawn = document.at(len(document) - 1).roi
        assert (drawn.x, drawn.y, drawn.width, drawn.height) == (700, 600, 200, 150)

    def test_the_stamp_follows_the_selected_box_being_resized(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:








        drag(view, _widget_point(300, 300), _widget_point(400, 400))

        assert view.stamp_size == (300, 300)
        assert _field(panel, "stamp-width").value() == 300

    def test_the_toggle_still_drives_the_view(self, view: VideoView, panel: CropToolsPanel) -> None:






        _toggle(panel, "mode-stamp").setChecked(True)
        assert view.mode is CropMode.STAMP

        _toggle(panel, "mode-draw").setChecked(True)
        assert view.mode is CropMode.DRAW





EDGE_BOX = ROI(x=900, y=100, width=80, height=80)

LOOSE_BOX = ROI(x=400, y=500, width=190, height=205)


@pytest.fixture
def rack(tab: ReplicateTab, document: ReplicateDocument) -> ReplicateDocument:

    del tab
    document.add_roi(LOOSE_BOX)
    document.add_roi(EDGE_BOX)
    return document


def _set_all(panel: CropToolsPanel, width: int, height: int) -> None:

    _field(panel, "stamp-width").setValue(width)
    _field(panel, "stamp-height").setValue(height)
    _button(panel, "set-all").click()


class TestSetAll:


    def test_every_replicate_takes_the_stamp_size(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:






        _set_all(panel, 200, 200)

        assert [(r.roi.width, r.roi.height) for r in rack.all()] == [(200, 200)] * 3

    def test_a_box_at_the_frame_edge_slides_instead_of_shrinking(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:








        _set_all(panel, 200, 200)

        edge = rack.at(2).roi
        assert (edge.width, edge.height) == (200, 200), "the box was trimmed, not slid"
        assert edge.right == 1000, "the box did not come to rest against the edge"

    def test_each_box_is_resized_about_its_own_centre(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:


        before = [_centre(replicate.roi) for replicate in rack.all()[:2]]

        _set_all(panel, 100, 100)

        after = [_centre(replicate.roi) for replicate in rack.all()[:2]]

        assert all(
            abs(a[0] - b[0]) <= 0.5 and abs(a[1] - b[1]) <= 0.5
            for a, b in zip(before, after, strict=True)
        )

    def test_the_whole_rack_is_one_undo_step(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:






        before_rois = [replicate.roi for replicate in rack.all()]
        before_count = rack.undo_stack.count()

        _set_all(panel, 200, 200)

        assert rack.undo_stack.count() == before_count + 1
        rack.undo_stack.undo()
        assert [replicate.roi for replicate in rack.all()] == before_rois

    def test_a_rack_already_at_that_size_records_no_history(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:

        _set_all(panel, 200, 200)
        settled = rack.undo_stack.count()

        _button(panel, "set-all").click()

        assert rack.undo_stack.count() == settled
