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
from sieve.gui.video_view import MIN_DRAG_PX, NO_SELECTION, VideoView
from tests.gui.qt_input import click, drag, move, press, release

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
