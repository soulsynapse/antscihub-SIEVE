"""The playback loop and the frontier it is folded against.

The loop can skip the window's last frame, which is the frame somebody timing
the end of a behaviour is waiting for. The window arithmetic it rides on is
`tests/unit/test_clip_window.py`; the strip's frame-to-column mapping, the
other half of this file before `gui/transport/` was drawn, is
`tests/unit/test_geometry.py`.

No Qt anywhere: the module is arithmetic, and these are numbers fed to it.
"""

from __future__ import annotations

import pytest

from sieve.core.pipeline_model import ClipRange
from sieve.gui.transport.pacing import feed_bounds, playback_step


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
