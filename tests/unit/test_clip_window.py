"""What survives an edit to a window: its length, or the edge that was grabbed.

Two things here are load-bearing and each fails for its own reason. The window
can lose its length under a body move, which is the failure the origin-plus-
length model exists to prevent. And a handle drag can move the edge that was
supposed to be pinned, which reads to the user as the box running away from the
frame they were holding it against.

No Qt anywhere: the module is arithmetic, and these are numbers fed to it.
"""

from __future__ import annotations

from fractions import Fraction

import pytest

from sieve.core.clip_window import (
    DEFAULT_WINDOW_SECONDS,
    containing,
    default_window,
    effective_window,
    ended_at,
    ended_at_handle,
    fitted,
    moved_to,
    started_at,
)
from sieve.core.pipeline_model import ClipRange

SOURCE_FRAMES = 1000

#: A one-second floor at 30 fps, which is what a handle drag on the strip carries.
FLOOR = 30

#: A whole rate, so the arithmetic below reads. `NTSC` is the one that has an
#: opinion about how the conversion is done.
RATE = Fraction(30)
NTSC = Fraction(30000, 1001)


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
        assert default_window(SOURCE_FRAMES, RATE) == ClipRange(
            start=0, end=int(DEFAULT_WINDOW_SECONDS * 30)
        )

    def test_a_shorter_asset_is_the_whole_asset(self) -> None:
        assert default_window(120, RATE) == ClipRange(start=0, end=120)

    def test_an_unusable_frame_rate_yields_the_whole_asset(self) -> None:
        """Ten seconds of nothing is not a length worth putting a user inside."""
        assert default_window(SOURCE_FRAMES, Fraction(0)) == ClipRange(start=0, end=SOURCE_FRAMES)

    def test_no_source_is_no_window(self) -> None:
        assert default_window(0, RATE) is None

    def test_the_absence_of_a_choice_survives_being_displayed(self) -> None:
        """The document keeps `None`; only the *display* falls back.

        A GUI that resolved this by writing the default into the document would
        make `Project.clip = None` unreachable, and `plan.py`'s whole-video
        fallback along with it.
        """
        assert effective_window(None, SOURCE_FRAMES, RATE) == ClipRange(start=0, end=300)
        chosen = ClipRange(start=10, end=20)
        assert effective_window(chosen, SOURCE_FRAMES, RATE) is chosen

    def test_a_caller_supplied_length_replaces_the_shipped_one(self) -> None:
        """What makes the length the GUI remembers reach the fallback at all."""
        assert default_window(SOURCE_FRAMES, RATE, 4.0) == ClipRange(start=0, end=120)
        assert effective_window(None, SOURCE_FRAMES, RATE, 4.0) == ClipRange(start=0, end=120)

    def test_a_remembered_length_does_not_displace_a_chosen_window(self) -> None:
        """The remembered length is the fallback, never an edit to a project."""
        chosen = ClipRange(start=10, end=20)
        assert effective_window(chosen, SOURCE_FRAMES, RATE, 4.0) is chosen

    def test_a_length_of_nothing_yields_the_whole_asset(self) -> None:
        """A store hand-edited to zero must not open a session in no frames."""
        assert default_window(SOURCE_FRAMES, RATE, 0.0) == ClipRange(start=0, end=SOURCE_FRAMES)

    def test_a_broadcast_rate_gets_the_frames_ten_seconds_covers(self) -> None:
        """299, not 300: ten seconds at 30000/1001 is 299.7 frames.

        The rounding this used to do handed back a window a frame longer than
        the length it was asked for, and `FrameCount.spanning` is where the
        truncation is argued. Exact arithmetic is what makes the answer 299
        rather than whichever side of 299.7 a double landed on.
        """
        assert default_window(SOURCE_FRAMES, NTSC) == ClipRange(start=0, end=299)

    def test_a_rate_too_slow_for_the_length_still_yields_a_frame(self) -> None:
        """The floor is what stops a truncation opening a window of nothing."""
        assert default_window(SOURCE_FRAMES, Fraction(1, 60), 10.0) == ClipRange(start=0, end=1)


class TestFittingOntoTheBoundSource:
    """A saved span against the video actually open, which may be a different one."""

    def test_a_window_landing_past_the_end_is_no_window(self) -> None:
        assert fitted(ClipRange(start=1200, end=1500), SOURCE_FRAMES) is None

    def test_a_window_overhanging_the_end_is_trimmed_to_it(self) -> None:
        assert fitted(ClipRange(start=900, end=1500), SOURCE_FRAMES) == ClipRange(
            start=900, end=SOURCE_FRAMES
        )
