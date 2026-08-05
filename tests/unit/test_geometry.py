"""The timeline strip's frame-to-column mapping.

The mapping can be off by a column at the first or last frame, which is exactly
where a user marking the start or the end of a video is looking and nowhere a
mid-band test would catch. The playback loop, the other half of this file
before `gui/timeline/` was drawn, is `tests/unit/test_pacing.py`.

No Qt anywhere: the module is arithmetic, and these are numbers fed to it.
"""

from __future__ import annotations

import pytest

from sieve.gui.timeline.geometry import Geometry

SOURCE_FRAMES = 1000


class TestGeometry:
    @pytest.fixture
    def geometry(self) -> Geometry:
        return Geometry(frame_count=SOURCE_FRAMES, width=500.0)

    @pytest.mark.parametrize("frame", [0, 1, 499, 998, 999])
    def test_a_column_maps_back_to_the_frame_that_owns_it(
        self, geometry: Geometry, frame: int
    ) -> None:
        """The round trip, at both ends and not only in the middle.

        A `width - 1` denominator — the obvious inverse, and the one V1 used —
        passes at 0 and in the middle and reaches the last frame one pixel
        early.
        """
        assert geometry.frame_at(geometry.centre_of_frame(frame)) == frame

    def test_the_asset_ends_at_the_right_edge(self, geometry: Geometry) -> None:
        """`frame_count` is not a frame; it is where a half-open span stops."""
        assert geometry.x_of_frame(SOURCE_FRAMES) == pytest.approx(500.0)
        assert geometry.x_of_frame(SOURCE_FRAMES - 1) < 500.0

    def test_a_click_past_either_edge_lands_on_a_real_frame(self, geometry: Geometry) -> None:
        """A drag does not stop at the widget's border; the mouse keeps arriving."""
        assert geometry.frame_at(-40.0) == 0
        assert geometry.frame_at(9999.0) == SOURCE_FRAMES - 1

    def test_a_one_frame_window_is_still_visible(self, geometry: Geometry) -> None:
        left, right = geometry.span(500, 501)
        assert right - left >= 2.0

    def test_widening_a_span_does_not_move_it(self, geometry: Geometry) -> None:
        left, _ = geometry.span(500, 501)
        assert left == pytest.approx(geometry.x_of_frame(500))

    def test_an_empty_geometry_maps_everything_to_nothing(self) -> None:
        """The state on startup and after closing a video, hit by every paint."""
        empty = Geometry(frame_count=0, width=500.0)
        assert empty.is_empty
        assert empty.frame_at(250.0) == 0
        assert empty.x_of_frame(10) == 0.0
