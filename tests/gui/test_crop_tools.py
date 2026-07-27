"""The crop tools as the tab wires them: one drag, one undo step.

`test_video_view.py` covers the gestures against the viewport in isolation —
what a press means, where a stamp lands, which handle wins a contested pixel.
What that file cannot see is the half of the item that lives in the *wiring*:
a drag emits geometry continuously, and whether sixty emissions become one undo
entry or sixty is decided by the token riding each one through the tab into
`SetReplicateROI.mergeWith`. So these tests hold a real `ReplicateTab` over a
real document and assert on the undo stack, which is the only place that
difference is visible.

The fixture geometry is the `document` fixture's 1000x800 source shown in an
800x600 viewport, matching `test_video_view.py` so the same hand-computed
widget points mean the same source pixels in both files.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QLabel, QSpinBox
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
    """Where a source pixel lands in widget coordinates, by hand."""
    return QPointF(INSET_X + source_x * SCALE, source_y * SCALE)


@pytest.fixture
def player(qapp: object) -> Iterator[VideoPlayer]:
    del qapp
    instance = VideoPlayer()
    yield instance
    instance.shutdown()


@pytest.fixture
def tab(qtbot: QtBot, player: VideoPlayer, document: ReplicateDocument) -> ReplicateTab:
    """A tab whose viewport is sized and bound, with one arena cut and selected."""
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


def slow_drag(view: VideoView, start: QPointF, *waypoints: QPointF) -> None:
    """A drag that actually travels, one distinct position at a time.

    `qt_input.drag` sends a single move straight to the destination, which is
    two emissions where the second repeats the first — and `set_roi` discards a
    no-op, so a merging bug is invisible under it: the stack gets one entry
    whether or not `mergeWith` does anything. Every test here about undo
    *granularity* therefore needs a gesture with distinct intermediate
    geometries, which is also what a real drag is.
    """
    press(view, start)
    for waypoint in waypoints:
        move(view, waypoint)
    release(view, waypoints[-1] if waypoints else start)


class TestUndoGranularity:
    #: Five distinct positions, so a gesture that failed to merge would leave
    #: five entries and the assertions below could tell the difference.
    WAYPOINTS = (
        _widget_point(220, 210),
        _widget_point(250, 220),
        _widget_point(280, 240),
        _widget_point(300, 250),
    )

    def test_one_drag_is_one_undo_step(self, view: VideoView, document: ReplicateDocument) -> None:
        """The item's own test. Many geometries, one entry.

        Without merging, Ctrl+Z walks the box backwards a pixel at a time and
        the user presses it forty times to undo one gesture they think of as
        one action.
        """
        before = document.undo_stack.count()

        slow_drag(view, _widget_point(200, 200), *self.WAYPOINTS)

        assert document.at(0).roi != BOX, "the drag did not move anything"
        assert document.undo_stack.count() == before + 1

    def test_undo_returns_the_box_to_where_the_drag_began(
        self, view: VideoView, document: ReplicateDocument
    ) -> None:
        """One Ctrl+Z, all the way back — not one waypoint back.

        Merging has to keep the *first* step's displaced geometry. Absorbing
        the later command's `_previous` instead would undo to the second-to-last
        waypoint, which looks like nothing happened until a user actually drags
        a box and presses Ctrl+Z once.
        """
        slow_drag(view, _widget_point(200, 200), *self.WAYPOINTS)
        assert document.at(0).roi != BOX

        document.undo_stack.undo()

        assert document.at(0).roi == BOX

    def test_two_drags_are_two_undo_steps(
        self, view: VideoView, document: ReplicateDocument
    ) -> None:
        """Merging is per gesture, not per pair of geometry commands.

        A token shared across gestures would collapse an afternoon of nudging
        into one entry, which is the same failure as sixty entries wearing the
        opposite sign.
        """
        before = document.undo_stack.count()

        slow_drag(view, _widget_point(200, 200), *self.WAYPOINTS)
        slow_drag(view, _widget_point(300, 250), _widget_point(330, 270), _widget_point(350, 300))

        assert document.undo_stack.count() == before + 2

    def test_a_typed_dimension_is_its_own_undo_step(
        self, panel: CropToolsPanel, document: ReplicateDocument
    ) -> None:
        """A discrete edit carries no token, so it merges with nothing."""
        before = document.undo_stack.count()

        _field(panel, "roi-x").setValue(400)
        _field(panel, "roi-y").setValue(500)

        assert document.undo_stack.count() == before + 2
        assert document.at(0).roi == ROI(x=400, y=500, width=200, height=200)

    def test_an_abandoned_drag_leaves_no_trace(
        self, view: VideoView, document: ReplicateDocument
    ) -> None:
        """Escape restores under the gesture's own token, so it collapses away.

        The entry survives — it is the one the drag was building — but it now
        describes no change, and the box is where it started.
        """
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
        """The numeric readout is live, which is what makes it a readout.

        And it must not feed back: the panel writing its own refreshed values
        into the document mid-drag would fight the cursor.
        """
        drag(view, _widget_point(200, 200), _widget_point(300, 250))

        assert _field(panel, "roi-x").value() == document.at(0).roi.x == 200
        assert _field(panel, "roi-width").value() == BOX.width

    def test_a_drawn_region_fills_the_stamp_fields(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:
        """Draw once, then stamp: the size has to arrive in the panel by itself."""
        drag(view, _widget_point(500, 400), _widget_point(637, 491))

        assert (_field(panel, "stamp-width").value(), _field(panel, "stamp-height").value()) == (
            137,
            91,
        )

    def test_typing_a_stamp_size_reaches_the_view(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:
        """The vision's other route to a stamp: entered by dimensions."""
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
        """`REFINED-VISION.md`: the information panel points at the parent."""
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
