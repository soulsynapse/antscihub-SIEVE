"""The timeline's arithmetic: the held length, the mapping, and the loop.

Three things here are load-bearing and each fails for its own reason. The
window can lose its length under an edit, which is the failure the origin-plus-
length model exists to prevent. The mapping can be off by a column at the first
or last frame, which is exactly where a user marking the start or the end of a
video is looking and nowhere a mid-band test would catch. And the loop can skip
the window's last frame, which is the frame somebody watching a behaviour end
is waiting for.

No Qt anywhere: the module is arithmetic, and these are numbers fed to it.
"""

from __future__ import annotations

import pytest

from sieve.core.pipeline_model import ClipRange
from sieve.gui.timeline_model import (
    DEFAULT_WINDOW_SECONDS,
    Geometry,
    containing,
    default_window,
    effective_window,
    ended_at,
    ended_at_handle,
    feed_bounds,
    fitted,
    moved_to,
    playback_step,
    started_at,
)

SOURCE_FRAMES = 1000

#: A one-second floor at 30 fps, which is what a handle drag on the strip carries.
FLOOR = 30


class TestTheWindowHoldsItsLength:
    def test_moving_the_origin_carries_the_length(self) -> None:
        window = ClipRange(start=100, end=400)
        assert moved_to(window, 600, SOURCE_FRAMES) == ClipRange(start=600, end=900)

    @pytest.mark.parametrize("origin", [900, 999, 5000])
    def test_a_window_pushed_off_the_end_rests_against_it_at_full_length(self, origin: int) -> None:
        """The rule the whole model exists for.

        Two independent marks would shorten the span here — silently, and the
        user's only way to notice is to read the length back.
        """
        window = ClipRange(start=100, end=400)
        moved = moved_to(window, origin, SOURCE_FRAMES)
        assert moved == ClipRange(start=700, end=1000)
        assert moved.frame_count == window.frame_count

    def test_a_window_longer_than_the_source_becomes_the_source(self) -> None:
        """Reachable on a short asset, where the length cannot be held at all."""
        window = ClipRange(start=0, end=5000)
        assert moved_to(window, 200, SOURCE_FRAMES) == ClipRange(start=0, end=SOURCE_FRAMES)

    def test_an_end_mark_resizes_rather_than_moving(self) -> None:
        window = ClipRange(start=100, end=400)
        assert ended_at(window, 199, SOURCE_FRAMES) == ClipRange(start=100, end=200)

    def test_an_end_before_the_origin_releases_the_origin(self) -> None:
        window = ClipRange(start=300, end=600)
        assert ended_at(window, 50, SOURCE_FRAMES) == ClipRange(start=0, end=51)

    def test_an_end_on_the_origin_leaves_a_single_frame(self) -> None:
        """`end == start` is a range `ClipRange` refuses to construct at all."""
        window = ClipRange(start=100, end=400)
        assert ended_at(window, 100, SOURCE_FRAMES) == ClipRange(start=100, end=101)


class TestTheBracketHandles:
    """A handle drag is the one window gesture that moves one edge and not the other.

    Each of these is a distinct way the pair can be wrong: the pinned edge can
    travel, the floor can be crossed, and a floor larger than the asset can
    produce a span that does not exist.
    """

    @pytest.fixture
    def window(self) -> ClipRange:
        return ClipRange(start=400, end=700)

    def test_the_left_handle_moves_the_start_and_pins_the_end(self, window: ClipRange) -> None:
        assert started_at(window, 250, SOURCE_FRAMES, FLOOR) == ClipRange(start=250, end=700)

    def test_the_right_handle_moves_the_end_and_pins_the_start(self, window: ClipRange) -> None:
        """Inclusive of the frame under the cursor, like every other out mark."""
        assert ended_at_handle(window, 799, SOURCE_FRAMES, FLOOR) == ClipRange(start=400, end=800)

    def test_a_left_drag_past_the_end_stops_at_the_floor(self, window: ClipRange) -> None:
        """Not `ended_at`'s release-the-origin rule: a held handle stops, it does not jump."""
        assert started_at(window, 690, SOURCE_FRAMES, FLOOR) == ClipRange(start=670, end=700)
        assert started_at(window, 5000, SOURCE_FRAMES, FLOOR) == ClipRange(start=670, end=700)

    def test_a_right_drag_past_the_start_stops_at_the_floor(self, window: ClipRange) -> None:
        assert ended_at_handle(window, 100, SOURCE_FRAMES, FLOOR) == ClipRange(start=400, end=430)

    def test_a_handle_dragged_off_the_source_stops_against_it(self, window: ClipRange) -> None:
        assert started_at(window, -50, SOURCE_FRAMES, FLOOR) == ClipRange(start=0, end=700)
        assert ended_at_handle(window, 5000, SOURCE_FRAMES, FLOOR) == ClipRange(
            start=400, end=SOURCE_FRAMES
        )

    def test_a_source_shorter_than_the_floor_is_its_own_floor(self) -> None:
        """Twenty frames of video cannot hold a one-second window, and must not pretend to."""
        window = ClipRange(start=0, end=20)
        assert started_at(window, 15, 20, FLOOR) == ClipRange(start=0, end=20)
        assert ended_at_handle(window, 2, 20, FLOOR) == ClipRange(start=0, end=20)


class TestContaining:
    @pytest.fixture
    def window(self) -> ClipRange:
        return ClipRange(start=400, end=700)

    def test_a_frame_already_inside_moves_nothing(self, window: ClipRange) -> None:
        assert containing(window, 500, SOURCE_FRAMES) is window

    def test_a_frame_before_it_becomes_the_first_frame(self, window: ClipRange) -> None:
        assert containing(window, 100, SOURCE_FRAMES) == ClipRange(start=100, end=400)

    def test_a_frame_after_it_becomes_the_last_frame(self, window: ClipRange) -> None:
        """Moved the least distance that contains it, not centred on it.

        Centring travels twice as far as asked and throws away the stretch the
        user was already looking at.
        """
        moved = containing(window, 800, SOURCE_FRAMES)
        assert moved == ClipRange(start=501, end=801)
        assert moved.end - 1 == 800


class TestTheDefaultWindow:
    def test_it_is_ten_seconds_at_the_head(self) -> None:
        assert default_window(SOURCE_FRAMES, 30.0) == ClipRange(
            start=0, end=int(DEFAULT_WINDOW_SECONDS * 30)
        )

    def test_a_shorter_asset_is_the_whole_asset(self) -> None:
        assert default_window(120, 30.0) == ClipRange(start=0, end=120)

    def test_an_unusable_frame_rate_yields_the_whole_asset(self) -> None:
        """Ten seconds of nothing is not a length worth putting a user inside."""
        assert default_window(SOURCE_FRAMES, 0.0) == ClipRange(start=0, end=SOURCE_FRAMES)

    def test_no_source_is_no_window(self) -> None:
        assert default_window(0, 30.0) is None

    def test_the_absence_of_a_choice_survives_being_displayed(self) -> None:
        """The document keeps `None`; only the *display* falls back.

        A GUI that resolved this by writing the default into the document would
        make `Project.clip = None` unreachable, and `plan.py`'s whole-video
        fallback along with it.
        """
        assert effective_window(None, SOURCE_FRAMES, 30.0) == ClipRange(start=0, end=300)
        chosen = ClipRange(start=10, end=20)
        assert effective_window(chosen, SOURCE_FRAMES, 30.0) is chosen

    def test_a_window_landing_past_the_end_is_no_window(self) -> None:
        assert fitted(ClipRange(start=1200, end=1500), SOURCE_FRAMES) is None
        assert fitted(ClipRange(start=900, end=1500), SOURCE_FRAMES) == ClipRange(
            start=900, end=SOURCE_FRAMES
        )


class TestPlaybackWraps:
    @pytest.fixture
    def window(self) -> ClipRange:
        return ClipRange(start=100, end=200)

    def test_a_target_inside_the_window_is_taken_as_it_is(self, window: ClipRange) -> None:
        step = playback_step(150, 149, window)
        assert (step.index, step.rewound) == (150, False)

    def test_the_last_frame_is_shown_before_the_wrap(self, window: ClipRange) -> None:
        """Playback drops frames it could not decode, so the clock overshoots.

        Without this the window's last frame is skipped on every lap — and it
        is the frame anybody timing the end of a behaviour is watching for.
        """
        step = playback_step(240, 187, window)
        assert (step.index, step.rewound) == (199, False)

    def test_the_wrap_happens_from_the_last_frame_and_re_anchors(self, window: ClipRange) -> None:
        step = playback_step(240, 199, window)
        assert (step.index, step.rewound) == (100, True)

    def test_a_playhead_left_behind_the_window_is_pulled_into_it(self, window: ClipRange) -> None:
        """Reachable by moving the window while playback is running."""
        step = playback_step(40, 40, window)
        assert (step.index, step.rewound) == (100, True)


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


class TestTheFrontierFold:
    """Render-fed playback's bound: play only what the render has produced."""

    def test_playback_is_confined_to_the_rendered_prefix(self) -> None:
        window = ClipRange(start=100, end=400)
        bounds = feed_bounds(window, 249)
        assert bounds == ClipRange(start=100, end=250)
        # And `playback_step` folds a clock past the frontier back to the
        # window's start — the loop over what exists, not a stall at its edge.
        assert playback_step(300, 249, bounds).index == window.start

    def test_a_frontier_past_the_window_end_changes_nothing(self) -> None:
        """The render's last frame is the window's; an overshoot must not widen it."""
        window = ClipRange(start=100, end=400)
        assert feed_bounds(window, 399) == window
        assert feed_bounds(window, 5000) == window

    def test_no_frontier_and_a_stale_frontier_both_yield_the_window(self) -> None:
        """Folding to nothing, or to a foreign span, would freeze the pane
        in the name of keeping it moving."""
        window = ClipRange(start=100, end=400)
        assert feed_bounds(window, None) == window
        assert feed_bounds(window, 99) == window

    def test_a_frontier_at_the_window_start_is_a_one_frame_loop(self) -> None:
        """The very start of a render: one frame exists and it is shown."""
        window = ClipRange(start=100, end=400)
        assert feed_bounds(window, 100) == ClipRange(start=100, end=101)
