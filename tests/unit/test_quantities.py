"""The four quantities: what each one refuses, and what the refusals buy.

Not a tour of the operators. Each test here pins a claim the types were
introduced to make, and would fail for a reason somebody could act on.

The one claim not tested here is the central one — that a `WorkUnits` cannot be
added to a `WallTime` — because it is enforced statically and pyright runs over
`src/` and `tests/` in the gate. A runtime assertion would be testing whichever
`AttributeError` the accessor names happen to produce, which is an accident of
spelling rather than the contract. `MediaTime` and `WallTime` both carry
`.seconds`, so that particular mixture is the one that would *not* raise if it
ever executed: it is refused where it is written, and nowhere else.
"""

from __future__ import annotations

import math
from fractions import Fraction

import pytest

from sieve.core.types import NO_FRAMES, FrameCount, MediaTime, WallTime, WorkUnits

#: 29.97 drop-frame, the rate every rational-fps argument is actually about.
NTSC = Fraction(30000, 1001)


class TestFrameCount:
    def test_a_negative_count_is_refused_where_it_is_written(self) -> None:
        """The check that used to live in `FilterSpec.__post_init__`.

        Moving it into the type moves it from registration — where the message
        names a filter somebody has to go and find — to the expression that
        computed the number, which is the one place the author is looking.
        """
        with pytest.raises(ValueError, match="non-negative"):
            FrameCount(-1)

        # And a subtraction that goes past zero is the same mistake arriving by
        # a different route: a shortfall taken the wrong way round.
        with pytest.raises(ValueError, match="non-negative"):
            assert FrameCount(3) - FrameCount(5)

    def test_crossing_a_rate_change_rounds_up_and_never_down(self) -> None:
        """`at_input_of` is the whole of the warmup conversion, and ceils.

        A rate of 3/2 means two input frames buy three output frames, so five
        output frames want 3.33 inputs and therefore 4. Flooring gives 3 and the
        node is one frame short of settled — behind a 10:1 decimator that same
        one-frame shortfall is ten source frames of an IIR that never converged,
        and the preview renders either way.
        """
        assert FrameCount(5).at_input_of(Fraction(3, 2)) == FrameCount(4)
        assert FrameCount(6).at_input_of(Fraction(3, 2)) == FrameCount(4)
        assert FrameCount(5).at_input_of(Fraction(1, 10)) == FrameCount(50)
        assert NO_FRAMES.at_input_of(Fraction(1, 10)) == NO_FRAMES

    def test_the_conversion_is_monotone(self) -> None:
        """What lets `plan._lead_in` fold instead of enumerating paths.

        A diamond has exponentially many root-to-node paths; the walk takes a
        maximum node by node instead, which is only equal to the maximum over
        paths because this conversion never decreases. Checked over a rate that
        divides exactly and one that does not, since a suite of decimators alone
        cannot tell the two roundings apart.
        """
        for rate in (Fraction(1, 10), Fraction(3, 2), Fraction(7, 3)):
            converted = [FrameCount(n).at_input_of(rate) for n in range(40)]
            assert converted == sorted(converted)

    def test_a_rate_that_could_not_be_supplied_is_refused(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            FrameCount(5).at_input_of(Fraction(0))


class TestMediaTime:
    def test_the_frame_grid_is_where_a_float_fps_loses_a_whole_frame(self) -> None:
        """Why media time is a `Fraction`, stated as the arithmetic that fails.

        The usual argument — that float seconds drift over a long recording —
        is not the one that bites: accumulating a float frame duration a
        million times is off by about 1e-6 frames. What bites is that every
        media time is eventually floored back onto the frame grid, and at
        30000/1001 the float product lands just below an integer. Fifteen
        frames converted to seconds and back is fourteen frames, on the second
        conversion, in the first second of footage.
        """
        fifteen = MediaTime.of_frames(FrameCount(15), NTSC)

        assert FrameCount.spanning(fifteen, NTSC) == FrameCount(15)
        assert math.floor(float(fifteen.seconds) * float(NTSC)) == 14

    def test_converting_frames_to_time_needs_an_fps_and_says_so(self) -> None:
        """A frame count is node-relative; the same 90 frames are two durations.

        Three seconds of 30 fps source, or thirty seconds of a 10:1 decimator's
        output. No default fps could be right for both, so there is none.
        """
        count = FrameCount(90)

        assert MediaTime.of_frames(count, Fraction(30)) == MediaTime(Fraction(3))
        assert MediaTime.of_frames(count, Fraction(3)) == MediaTime(Fraction(30))

        with pytest.raises(ValueError, match="must be positive"):
            MediaTime.of_frames(count, Fraction(0))

    def test_a_partial_frame_is_not_a_frame(self) -> None:
        """`spanning` truncates: it answers how many frames are certain.

        A window of one second at 29.97 covers 29 whole frames and part of a
        thirtieth. Rounding up would hand back a frame that is only partly
        inside the window a user drew, and the count denominated against it —
        which is what a detection reports — would be over by one.
        """
        assert FrameCount.spanning(MediaTime(Fraction(1)), NTSC) == FrameCount(29)
        assert FrameCount.spanning(MediaTime(Fraction(1)), Fraction(30)) == FrameCount(30)


class TestWorkAndWallTime:
    def test_work_cannot_be_read_as_a_duration(self) -> None:
        """The rule this type exists for, guarded against a future convenience.

        A work estimate divided by a rate is a wall time *on one machine with
        one backend at one moment*, and the quotient does not carry which. The
        moment `WorkUnits` grows a `.milliseconds` — or a `.seconds`, or an
        `as_wall_time()` — the estimate becomes indistinguishable from a
        reading, and `docs/todo/work-units-have-one-anchor.md` is the item that
        has to name the anchor before anything may divide by it.
        """
        clock_names = {"seconds", "milliseconds", "ms", "as_wall_time", "elapsed"}

        assert clock_names.isdisjoint(dir(WorkUnits(1.0)))

    def test_wall_time_headroom_keeps_its_sign(self) -> None:
        """Unlike a frame count, a wall-clock difference may be negative.

        `bench/budgets.Budget.exceeded_by` reports headroom as a negative
        overage. Clamping at zero would make "just made it" and "made it by a
        mile" the same number, which is the direction rule 6 refuses — and it is
        why only `FrameCount` is a count.
        """
        under = WallTime.of_milliseconds(80.0) - WallTime.of_milliseconds(100.0)

        assert under.milliseconds == pytest.approx(-20.0)
        assert under < WallTime(0.0)
