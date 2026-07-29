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
        """A derived crop must not hide which source it came from."""
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


#: The drag that cuts a 137x91 arena, in source pixels, for the class below.
FIRST_DRAW = (_widget_point(500, 400), _widget_point(637, 491))


class TestStampByDefault:
    """Draw once, then click: what the toggle says, and what size lands.

    Three claims from one line of the vision — "stamp should be the default
    once one is drawn … it should stamp based on the highlighted replicate" —
    and they fail in three different places, which is why they are three tests.
    The first is about two widgets agreeing, the second about which of two
    remembered sizes wins, the third about the flip not costing the gesture it
    replaced.
    """

    def test_a_completed_draw_puts_both_widgets_in_stamp_mode(
        self, view: VideoView, panel: CropToolsPanel
    ) -> None:
        """The view flips itself, and the panel has to come with it.

        The mode used to be a one-way panel→view push, under which the view
        could not flip at all — and a version that flipped anyway would leave
        the radio buttons reading "Draw" while clicks stamped, which is rule 6's
        mirror direction: a control looking more truthful than it is.
        """
        assert view.mode is CropMode.DRAW

        drag(view, *FIRST_DRAW)

        assert view.mode is CropMode.STAMP
        assert _toggle(panel, "mode-stamp").isChecked()
        assert not _toggle(panel, "mode-draw").isChecked()

    def test_a_click_stamps_the_highlighted_replicate_not_the_last_drawn(
        self, view: VideoView, panel: CropToolsPanel, document: ReplicateDocument
    ) -> None:
        """The claim the previous behaviour got wrong.

        `_stamp_size` was whatever was drawn or typed last, with no relation to
        the selection. Draw a 137x91 arena, go back to the 200x200 one, and a
        stamp placing 137x91 would be placing the size of a box the user is no
        longer looking at. The panel field is asserted alongside because the
        stamp size is *written* rather than read at placement — if the two ever
        disagree, the field is the one telling the lie.
        """
        drag(view, *FIRST_DRAW)
        assert (document.at(1).roi.width, document.at(1).roi.height) == (137, 91)
        # The drawn box is the selection now, so the stamp is already following
        # it and not merely remembering the draw. Without this the assertion
        # below passes by coincidence: adding a row rebuilds the overlay while
        # the view still holds the *old* selection, which leaves 200x200 behind
        # for the wrong reason.
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
        """The flip must cost nothing, or it is a mode switch wearing a default.

        Stamp mode is consulted only for a click that travelled nowhere, so a
        second arena of a new size is still one drag — no trip back to the
        radio buttons to draw it, and no trip forward to stamp it again.
        """
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
        """ "The highlighted replicate" moves without the highlight moving.

        A handle drag changes the size of the box the user is looking at
        without changing *which* box it is, so a stamp size synced only on
        selection would go stale the moment a rack was tuned — which is the one
        gesture that happens between cutting the first arena and stamping the
        rest of them.
        """
        drag(view, _widget_point(300, 300), _widget_point(400, 400))

        assert view.stamp_size == (300, 300)
        assert _field(panel, "stamp-width").value() == 300

    def test_the_toggle_still_drives_the_view(self, view: VideoView, panel: CropToolsPanel) -> None:
        """Ownership moved to the view; the panel is still how a user asks.

        Asserted through the widget rather than the signal because the round
        trip is the part that could break: checking a button emits a request,
        which sets the mode, which announces, which checks the button again.
        """
        _toggle(panel, "mode-stamp").setChecked(True)
        assert view.mode is CropMode.STAMP

        _toggle(panel, "mode-draw").setChecked(True)
        assert view.mode is CropMode.DRAW


#: A box hard against the right edge of the 1000x800 source, small enough that
#: making it match the rack has to push it left. This is the row every
#: assertion about the frame edge below is about.
EDGE_BOX = ROI(x=900, y=100, width=80, height=80)
#: An ordinary interior box, hand-drawn a little off the rack's size.
LOOSE_BOX = ROI(x=400, y=500, width=190, height=205)


@pytest.fixture
def rack(tab: ReplicateTab, document: ReplicateDocument) -> ReplicateDocument:
    """Three replicates of three different sizes — a hand-cut rack."""
    del tab
    document.add_roi(LOOSE_BOX)
    document.add_roi(EDGE_BOX)
    return document


def _set_all(panel: CropToolsPanel, width: int, height: int) -> None:
    """Type a stamp size and press the button, as a user does."""
    _field(panel, "stamp-width").setValue(width)
    _field(panel, "stamp-height").setValue(height)
    _button(panel, "set-all").click()


class TestSetAll:
    """Set-all must update the whole rack, not only the selected crop."""

    def test_every_replicate_takes_the_stamp_size(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:
        """The operation itself, driven through the button rather than the document.

        Through the button because the panel emitting a size the tab never
        connects is the failure this cannot otherwise see, and it looks exactly
        like nothing happening.
        """
        _set_all(panel, 200, 200)

        assert [(r.roi.width, r.roi.height) for r in rack.all()] == [(200, 200)] * 3

    def test_a_box_at_the_frame_edge_slides_instead_of_shrinking(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:
        """The correctness condition, and the reason `ROI.placed_in` exists.

        `EDGE_BOX` centred at x=940 wants to become 200 wide, which would run
        60 px past the right edge of a 1000 px frame. Trimming it — which is
        what `clamped_to` and therefore `_fit` would do — returns a 160-wide box
        and leaves the rack non-uniform in exactly the case the user pressed
        this button to fix, while every number on screen says it worked.
        """
        _set_all(panel, 200, 200)

        edge = rack.at(2).roi
        assert (edge.width, edge.height) == (200, 200), "the box was trimmed, not slid"
        assert edge.right == 1000, "the box did not come to rest against the edge"

    def test_each_box_is_resized_about_its_own_centre(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:
        """Origin-preserving would compile, look right on a uniform rack, and
        walk every box half the size difference off its arena."""
        before = [_centre(replicate.roi) for replicate in rack.all()[:2]]

        _set_all(panel, 100, 100)

        after = [_centre(replicate.roi) for replicate in rack.all()[:2]]
        # Within half a pixel: an odd size difference cannot be split evenly.
        assert all(
            abs(a[0] - b[0]) <= 0.5 and abs(a[1] - b[1]) <= 0.5
            for a, b in zip(before, after, strict=True)
        )

    def test_the_whole_rack_is_one_undo_step(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:
        """Three rows, one entry, and one Ctrl+Z that returns all three.

        A loop pushing `SetReplicateROI` per row passes every assertion above
        and fails here: merging cannot collapse commands that name different
        rows, so the user would undo a twelve-arena rack one arena at a time.
        """
        before_rois = [replicate.roi for replicate in rack.all()]
        before_count = rack.undo_stack.count()

        _set_all(panel, 200, 200)

        assert rack.undo_stack.count() == before_count + 1
        rack.undo_stack.undo()
        assert [replicate.roi for replicate in rack.all()] == before_rois

    def test_a_rack_already_at_that_size_records_no_history(
        self, panel: CropToolsPanel, rack: ReplicateDocument
    ) -> None:
        """The second press changes nothing and must not say it did."""
        _set_all(panel, 200, 200)
        settled = rack.undo_stack.count()

        _button(panel, "set-all").click()

        assert rack.undo_stack.count() == settled
