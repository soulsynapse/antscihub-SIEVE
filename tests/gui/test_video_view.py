"""Widget-to-source coordinate handling and drag interpretation.

The viewport letterboxes, so widget pixels are neither the same scale nor the
same origin as source pixels. Every test here fixes a 800x600 widget over a
1000x800 source, which pillarboxes to a 750x600 content rect inset 25 px from
the left — deliberately not a round scale factor, because a 1:1 fixture would
pass even if the mapping ignored the letterbox entirely.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from pytestqt.qtbot import QtBot

from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.gui.video_view import (
    MAX_ZOOM,
    MIN_DRAG_PX,
    MIN_ZOOM,
    NO_SELECTION,
    CropMode,
    VideoView,
)
from tests.gui.qt_input import click, drag, move, press, release, wheel

pytestmark = pytest.mark.gui

WIDGET_SIZE = (800, 600)
SOURCE_SIZE = (1000, 800)
#: Left inset and scale of the content rect for the fixture geometry above.
INSET_X = 25.0
SCALE = 0.75

#: Rounding in `to_source` is to the nearest widget pixel, which at this scale
#: is 1.33 source pixels — so a round trip is allowed to move by one.
ROUND_TRIP_TOLERANCE = 1


@pytest.fixture
def view(qtbot: QtBot) -> VideoView:
    """A sized viewport bound to a 1000x800 source."""
    widget = VideoView()
    qtbot.addWidget(widget)
    widget.resize(*WIDGET_SIZE)
    widget.set_source_size(SOURCE_SIZE)
    return widget


def _widget_point(source_x: float, source_y: float) -> QPointF:
    """Where a source pixel lands in widget coordinates, by hand."""
    return QPointF(INSET_X + source_x * SCALE, source_y * SCALE)


class TestContentRect:
    def test_the_source_is_letterboxed_inside_the_widget(self, view: VideoView) -> None:
        content = view.content_rect()
        assert (content.x(), content.y()) == (INSET_X, 0.0)
        assert (content.width(), content.height()) == (750.0, 600.0)

    def test_without_a_source_the_content_is_the_whole_widget(self, view: VideoView) -> None:
        view.set_source_size(None)
        content = view.content_rect()
        assert (content.width(), content.height()) == WIDGET_SIZE


class TestToSource:
    @pytest.mark.parametrize(
        ("point", "expected"),
        [
            (QPointF(INSET_X, 0.0), (0, 0)),
            (QPointF(INSET_X + 750.0, 600.0), (1000, 800)),
            (QPointF(INSET_X + 375.0, 300.0), (500, 400)),
        ],
    )
    def test_corners_and_centre_map_exactly(
        self, view: VideoView, point: QPointF, expected: tuple[int, int]
    ) -> None:
        assert view.to_source(point) == expected

    @pytest.mark.parametrize(
        ("point", "expected"),
        [
            (QPointF(0.0, -50.0), (0, 0)),
            (QPointF(799.0, 599.0), (1000, 799)),
        ],
    )
    def test_the_letterbox_margins_clamp_into_the_frame(
        self, view: VideoView, point: QPointF, expected: tuple[int, int]
    ) -> None:
        """A drag that overshoots the frame edge yields the edge, not a negative."""
        assert view.to_source(point) == expected

    def test_without_a_source_everything_is_the_origin(self, view: VideoView) -> None:
        view.set_source_size(None)
        assert view.to_source(QPointF(400.0, 300.0)) == (0, 0)

    def test_a_degenerate_source_does_not_divide_by_zero(self, view: VideoView) -> None:
        view.set_source_size((0, 0))
        assert view.to_source(QPointF(400.0, 300.0)) == (0, 0)


class TestRoundTrip:
    @pytest.mark.parametrize(
        "roi",
        [
            ROI(x=0, y=0, width=1000, height=800),
            ROI(x=10, y=20, width=100, height=80),
            ROI(x=499, y=399, width=1, height=1),
            ROI(x=900, y=700, width=100, height=100),
        ],
    )
    def test_source_to_widget_to_source_survives(self, view: VideoView, roi: ROI) -> None:
        rect = view.to_widget(roi)
        top_left = view.to_source(rect.topLeft())
        bottom_right = view.to_source(rect.bottomRight())
        for got, expected in zip(
            top_left + bottom_right,
            (roi.x, roi.y, roi.right, roi.bottom),
            strict=True,
        ):
            assert abs(got - expected) <= ROUND_TRIP_TOLERANCE

    def test_a_widget_rect_is_the_source_rect_scaled_and_offset(self, view: VideoView) -> None:
        rect = view.to_widget(ROI(x=100, y=80, width=400, height=320))
        assert (rect.x(), rect.y()) == (INSET_X + 75.0, 60.0)
        assert (rect.width(), rect.height()) == (300.0, 240.0)

    def test_without_a_source_a_roi_has_no_rect(self, view: VideoView) -> None:
        view.set_source_size(None)
        assert view.to_widget(ROI(x=0, y=0, width=10, height=10)).isNull()


class TestDrawing:
    def test_a_drag_reports_a_roi_in_source_pixels(self, view: VideoView) -> None:
        drawn: list[ROI] = []
        view.roi_drawn.connect(drawn.append)
        drag(view, _widget_point(100, 80), _widget_point(500, 400))
        assert drawn == [ROI(x=100, y=80, width=400, height=320)]

    def test_a_drag_backwards_normalises(self, view: VideoView) -> None:
        drawn: list[ROI] = []
        view.roi_drawn.connect(drawn.append)
        drag(view, _widget_point(500, 400), _widget_point(100, 80))
        assert drawn == [ROI(x=100, y=80, width=400, height=320)]

    def test_a_short_drag_is_a_click_not_a_box(self, view: VideoView) -> None:
        drawn: list[ROI] = []
        selected: list[int] = []
        view.roi_drawn.connect(drawn.append)
        view.selection_requested.connect(selected.append)

        start = _widget_point(100, 80)
        drag(view, start, start + QPointF(MIN_DRAG_PX - 1, MIN_DRAG_PX - 1))

        assert drawn == []
        assert selected == [NO_SELECTION]

    def test_a_drag_flat_in_one_axis_is_not_a_box(self, view: VideoView) -> None:
        """A one-pixel-tall replicate is never what the user meant."""
        drawn: list[ROI] = []
        view.roi_drawn.connect(drawn.append)
        start = _widget_point(100, 80)
        drag(view, start, start + QPointF(400.0, 1.0))
        assert drawn == []

    def test_escape_abandons_the_drag(self, view: VideoView) -> None:
        drawn: list[ROI] = []
        view.roi_drawn.connect(drawn.append)

        press(view, _widget_point(100, 80))
        move(view, _widget_point(500, 400))
        view.keyPressEvent(
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        )
        release(view, _widget_point(500, 400))

        assert drawn == []

    def test_a_drag_without_a_source_does_nothing(self, view: VideoView) -> None:
        view.set_source_size(None)
        drawn: list[ROI] = []
        selected: list[int] = []
        view.roi_drawn.connect(drawn.append)
        view.selection_requested.connect(selected.append)

        drag(view, QPointF(100.0, 100.0), QPointF(400.0, 400.0))

        assert drawn == []
        assert selected == []


class TestSelection:
    @staticmethod
    def _replicate(name: str, roi: ROI) -> Replicate:
        return Replicate(roi=roi, name=name)

    def test_a_click_inside_a_box_selects_its_row(self, view: VideoView) -> None:
        view.set_replicates(
            [
                self._replicate("one", ROI(x=0, y=0, width=200, height=200)),
                self._replicate("two", ROI(x=400, y=400, width=200, height=200)),
            ]
        )
        selected: list[int] = []
        view.selection_requested.connect(selected.append)

        click(view, _widget_point(500, 500))

        assert selected == [1]

    def test_overlapping_boxes_select_the_topmost(self, view: VideoView) -> None:
        view.set_replicates(
            [
                self._replicate("under", ROI(x=0, y=0, width=600, height=600)),
                self._replicate("over", ROI(x=100, y=100, width=200, height=200)),
            ]
        )
        selected: list[int] = []
        view.selection_requested.connect(selected.append)

        click(view, _widget_point(200, 200))

        assert selected == [1]

    def test_a_click_on_empty_space_clears_the_selection(self, view: VideoView) -> None:
        view.set_replicates([self._replicate("one", ROI(x=0, y=0, width=200, height=200))])
        selected: list[int] = []
        view.selection_requested.connect(selected.append)

        click(view, _widget_point(800, 700))

        assert selected == [NO_SELECTION]

    def test_clearing_the_source_clears_the_overlay(self, view: VideoView) -> None:
        view.set_replicates([self._replicate("one", ROI(x=0, y=0, width=200, height=200))])
        view.set_selected(0)
        view.set_source_size(None)

        view.set_source_size(SOURCE_SIZE)
        selected: list[int] = []
        view.selection_requested.connect(selected.append)
        click(view, _widget_point(100, 100))

        assert selected == [NO_SELECTION]


class TestMagnifier:
    """Scroll to magnify, with a floor at the natural fit."""

    def test_scrolling_out_never_zooms_past_the_fit(self, view: VideoView) -> None:
        """The vision's rule, and the one a naive `scale *= 0.9` breaks.

        The literal `1.0` is deliberate, and asserting against `MIN_ZOOM`
        instead was a bug in an earlier draft of this test: the constant is the
        *definition* of the floor, so a test that reads it cannot observe the
        floor moving — lowering `MIN_ZOOM` to 0.1 moved the code and the
        assertion together and the test went on passing. 1.0 is the fit scale by
        construction, whatever the widget size, so it is a fact about the
        widget rather than a restatement of the source.

        The rect is checked for exact equality with `content_rect`, not
        approximate: a floor implemented by clamping a running product lands a
        float epsilon under the fit and leaves a hairline of letterbox inside
        the frame, which is a visible symptom nobody traces back to arithmetic.
        """
        centre = QPointF(400.0, 300.0)
        wheel(view, centre, 3)
        for _ in range(40):
            wheel(view, centre, -1)

        assert view.zoom == 1.0
        assert view.view_rect() == view.content_rect()

    def test_the_rect_covers_the_fit_at_every_step_of_a_scroll_out(self, view: VideoView) -> None:
        """The floor holds *during* the storm, not merely at the end of it.

        A clamp applied only when the wheel stops would let an intermediate
        frame paint smaller than the fit — one flickering frame of letterbox
        inside the picture per detent.
        """
        centre = QPointF(400.0, 300.0)
        wheel(view, centre, 6)

        for _ in range(30):
            wheel(view, centre, -1)
            view_rect, fit = view.view_rect(), view.content_rect()
            assert view_rect.width() >= fit.width()
            assert view_rect.height() >= fit.height()

    def test_magnification_is_bounded_above(self, view: VideoView) -> None:
        for _ in range(60):
            wheel(view, QPointF(400.0, 300.0), 1)
        assert view.zoom == MAX_ZOOM

    def test_the_point_under_the_cursor_stays_under_the_cursor(self, view: VideoView) -> None:
        """Anchoring, which is what makes the magnifier usable for placement.

        The anchor is deliberately off-centre and away from every edge, so a
        pass would mean the pan actually tracked rather than that the clamp
        happened to hold the rect still.
        """
        anchor = _widget_point(250, 200)
        before = view.source_at(anchor)

        wheel(view, anchor, 4)

        after = view.source_at(anchor)
        assert view.zoom > MIN_ZOOM
        assert after.x() == pytest.approx(before.x())
        assert after.y() == pytest.approx(before.y())

    @pytest.mark.parametrize(
        "roi",
        [
            ROI(x=10, y=20, width=100, height=80),
            ROI(x=499, y=399, width=1, height=1),
            ROI(x=900, y=700, width=100, height=100),
        ],
    )
    def test_a_round_trip_survives_magnification_and_pan(self, view: VideoView, roi: ROI) -> None:
        """`TestRoundTrip`'s invariant under a scale and an offset at once.

        The mapping had one free parameter — the fit — when the existing round
        trip was written, and now it has three. A pan without a zoom cannot
        occur, so the two are tested together; separately, a `to_widget` that
        applied the zoom but not the pan would still pass.
        """
        wheel(view, _widget_point(250, 200), 5)

        rect = view.to_widget(roi)
        top_left = view.to_source(rect.topLeft())
        bottom_right = view.to_source(rect.bottomRight())

        for got, expected in zip(
            top_left + bottom_right,
            (roi.x, roi.y, roi.right, roi.bottom),
            strict=True,
        ):
            assert abs(got - expected) <= ROUND_TRIP_TOLERANCE

    def test_a_new_source_returns_to_the_fit(self, view: VideoView) -> None:
        """Zoom is a view of *this* video and does not carry to the next one."""
        wheel(view, QPointF(400.0, 300.0), 4)
        view.set_source_size((640, 480))
        assert view.zoom == MIN_ZOOM


class TestStamp:
    """Place a remembered size, exactly."""

    STAMP = (137, 91)

    @pytest.fixture
    def stamping(self, view: VideoView) -> VideoView:
        view.set_mode(CropMode.STAMP)
        view.set_stamp_size(*self.STAMP)
        return view

    @pytest.mark.parametrize(
        "centre",
        [(500, 400), (301, 277), (777, 123), (250, 650)],
    )
    def test_a_stamp_places_the_drawn_size_exactly(
        self, stamping: VideoView, centre: tuple[int, int]
    ) -> None:
        """The invariant the whole stamp exists for.

        A rack is a dozen arenas of identical size. If placement rounded
        through widget coordinates — where one source pixel is 0.75 of a screen
        pixel at this fixture's scale — the twelve would differ by a pixel here
        and there, `equivalence_groups` would report them as one group, and the
        pixels would disagree. So the assertion is on the extent alone, at four
        placements chosen to round differently from each other.
        """
        drawn: list[ROI] = []
        stamping.roi_drawn.connect(drawn.append)

        click(stamping, _widget_point(*centre))

        assert len(drawn) == 1
        assert (drawn[0].width, drawn[0].height) == self.STAMP

    def test_a_stamp_at_the_edge_slides_rather_than_shrinks(self, stamping: VideoView) -> None:
        """Against a corner there is nowhere to centre, and the size still wins."""
        drawn: list[ROI] = []
        stamping.roi_drawn.connect(drawn.append)

        click(stamping, _widget_point(2, 2))

        assert drawn == [ROI(x=0, y=0, width=self.STAMP[0], height=self.STAMP[1])]

    def test_a_drag_still_draws_and_redefines_the_stamp(self, stamping: VideoView) -> None:
        """Stamp mode does not disable drawing — drawing is how a size is set."""
        drawn: list[ROI] = []
        sizes: list[tuple[int, int]] = []

        def record_size(width: int, height: int) -> None:
            sizes.append((width, height))

        stamping.roi_drawn.connect(drawn.append)
        stamping.stamp_size_changed.connect(record_size)

        drag(stamping, _widget_point(100, 80), _widget_point(500, 400))

        assert drawn == [ROI(x=100, y=80, width=400, height=320)]
        assert sizes == [(400, 320)]
        assert stamping.stamp_size == (400, 320)

    def test_without_a_size_a_stamp_click_is_only_a_selection(self, view: VideoView) -> None:
        """Nothing has been drawn yet, so there is no size to place."""
        view.set_mode(CropMode.STAMP)
        drawn: list[ROI] = []
        selected: list[int] = []
        view.roi_drawn.connect(drawn.append)
        view.selection_requested.connect(selected.append)

        click(view, _widget_point(500, 400))

        assert drawn == []
        assert selected == [NO_SELECTION]

    def test_a_stamp_click_on_a_box_selects_it_instead(self, stamping: VideoView) -> None:
        """Placing needs empty space; a box under the cursor is still a target."""
        stamping.set_replicates(
            [Replicate(roi=ROI(x=400, y=300, width=200, height=200), name="one")]
        )
        drawn: list[ROI] = []
        selected: list[int] = []
        stamping.roi_drawn.connect(drawn.append)
        stamping.selection_requested.connect(selected.append)

        click(stamping, _widget_point(500, 400))

        assert drawn == []
        assert selected == [0]


class TestAdjustment:
    """Moving and resizing the selected box."""

    BOX = ROI(x=100, y=100, width=200, height=200)

    @pytest.fixture
    def selected(self, view: VideoView) -> VideoView:
        view.set_replicates([Replicate(roi=self.BOX, name="one")])
        view.set_selected(0)
        return view

    @staticmethod
    def _adjustments(view: VideoView) -> list[tuple[int, ROI, int, str]]:
        recorded: list[tuple[int, ROI, int, str]] = []

        def record(row: int, roi: ROI, token: int, verb: str) -> None:
            recorded.append((row, roi, token, verb))

        view.roi_adjusted.connect(record)
        return recorded

    def test_dragging_the_body_translates_and_keeps_the_size(self, selected: VideoView) -> None:
        recorded = self._adjustments(selected)
        drawn: list[ROI] = []
        selected.roi_drawn.connect(drawn.append)

        drag(selected, _widget_point(200, 200), _widget_point(300, 250))

        assert drawn == [], "a drag inside the selected box drew a new region"
        assert recorded[-1][0] == 0
        assert recorded[-1][1] == ROI(x=200, y=150, width=200, height=200)
        assert recorded[-1][3] == "Move"

    def test_a_move_against_the_frame_edge_slides_and_keeps_its_size(
        self, selected: VideoView
    ) -> None:
        """The counterpart to the stamp's rule, arriving through the other gesture."""
        recorded = self._adjustments(selected)

        drag(selected, _widget_point(200, 200), _widget_point(20, 20))

        assert recorded[-1][1] == ROI(x=0, y=0, width=200, height=200)

    def test_a_move_along_one_axis_is_still_a_move(self, selected: VideoView) -> None:
        """The drawing rule wants extent in both axes; adjusting must not.

        Sliding a box horizontally along a rack is the commonest adjustment
        there is, and under the both-axes rule it releases as a *click* — which
        the tab reads as accepting the replicate and navigating away from the
        tab the user is still working in.
        """
        recorded = self._adjustments(selected)
        chosen: list[int] = []
        selected.selection_requested.connect(chosen.append)

        drag(selected, _widget_point(200, 200), _widget_point(400, 200))

        assert chosen == [], "a horizontal move was read as a click"
        assert recorded[-1][1] == ROI(x=300, y=100, width=200, height=200)

    def test_dragging_a_corner_handle_resizes(self, selected: VideoView) -> None:
        recorded = self._adjustments(selected)

        drag(selected, _widget_point(100, 100), _widget_point(50, 60))

        assert recorded[-1][1] == ROI(x=50, y=60, width=250, height=240)
        assert recorded[-1][3] == "Resize"

    def test_dragging_an_edge_handle_moves_only_that_edge(self, selected: VideoView) -> None:
        recorded = self._adjustments(selected)

        drag(selected, _widget_point(300, 200), _widget_point(400, 250))

        assert recorded[-1][1] == ROI(x=100, y=100, width=300, height=200)

    def test_every_step_of_one_drag_shares_a_token(self, selected: VideoView) -> None:
        """What lets the undo stack collapse a drag; the tab relies on it."""
        recorded = self._adjustments(selected)

        press(selected, _widget_point(200, 200))
        move(selected, _widget_point(250, 220))
        move(selected, _widget_point(300, 250))
        release(selected, _widget_point(300, 250))

        tokens = {entry[2] for entry in recorded}
        assert len(recorded) >= 3
        assert len(tokens) == 1

    def test_two_drags_do_not_share_a_token(self, selected: VideoView) -> None:
        recorded = self._adjustments(selected)

        drag(selected, _widget_point(200, 200), _widget_point(300, 250))
        selected.set_replicates([Replicate(roi=recorded[-1][1], name="one")])
        drag(selected, _widget_point(300, 250), _widget_point(400, 300))

        assert recorded[0][2] != recorded[-1][2]

    def test_a_handle_outside_its_box_beats_the_box_behind_it(self, view: VideoView) -> None:
        """The ordering rule, stated as the bug it prevents.

        The small box is on top and selected; its top-left handle straddles its
        own corner, so the outer half of that handle lies inside the *large*
        box behind. Containment-first hands that half to the large box, and the
        corner of the selected box becomes unreachable — the press starts a new
        drawn region instead of a resize.
        """
        view.set_replicates(
            [
                Replicate(roi=ROI(x=0, y=0, width=600, height=600), name="under"),
                Replicate(roi=ROI(x=100, y=100, width=200, height=200), name="over"),
            ]
        )
        view.set_selected(1)
        recorded = self._adjustments(view)
        drawn: list[ROI] = []
        view.roi_drawn.connect(drawn.append)

        corner = _widget_point(100, 100)
        outside_the_box_but_on_the_handle = corner - QPointF(4.0, 4.0)
        drag(view, outside_the_box_but_on_the_handle, _widget_point(50, 50))

        assert drawn == [], "the press was read as drawing a new region"
        assert recorded[-1][0] == 1
        assert recorded[-1][1].x == 50

    def test_a_click_on_the_selected_box_still_accepts_it(self, selected: VideoView) -> None:
        """Adjust and accept share a press; only travel tells them apart."""
        recorded = self._adjustments(selected)
        chosen: list[int] = []
        selected.selection_requested.connect(chosen.append)

        click(selected, _widget_point(200, 200))

        assert chosen == [0]
        assert recorded == []

    def test_escape_puts_an_adjusted_box_back(self, selected: VideoView) -> None:
        """And under the gesture's own token, so the whole drag collapses away."""
        recorded = self._adjustments(selected)

        press(selected, _widget_point(200, 200))
        move(selected, _widget_point(400, 350))
        selected.keyPressEvent(
            QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        )

        assert recorded[-1][1] == self.BOX
        assert recorded[-1][2] == recorded[0][2]

    def test_an_unselected_box_has_no_handles(self, view: VideoView) -> None:
        """A dozen arenas do not wear ninety-six grab targets between them."""
        view.set_replicates([Replicate(roi=self.BOX, name="one")])
        recorded = self._adjustments(view)
        drawn: list[ROI] = []
        view.roi_drawn.connect(drawn.append)

        drag(view, _widget_point(100, 100), _widget_point(50, 60))

        assert recorded == []
        assert len(drawn) == 1
