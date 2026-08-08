"""Where playback goes next inside the span it is confined to.

Qt-free, like `coalescer.py` and `scrub_policy.py`, and for the same reason:
every rule here is wrong at the first or the last frame of a window before it
is right anywhere, and feeding these functions numbers is the whole test.

The frame-to-column mapping the band paints is `timeline/geometry.py`; this is
the half only `player.py` consumes. They are apart so that `transport` and
`timeline` do not import each other.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.core.pipeline_model import SourceSpan


@dataclass(frozen=True, slots=True)
class PlaybackStep:
    """Where playback goes next, and whether the clock has to be re-anchored.

    Two fields because a wrap is not a seek. The player drives from elapsed wall
    time, so returning to the window's start without saying so would leave the
    anchor at the previous lap and the next tick would compute a target one
    whole lap ahead.
    """

    index: int
    rewound: bool


def playback_step(target: int, current: int, window: SourceSpan) -> PlaybackStep:
    """Fold a wall-clock target into `[start, end)`, looping at the end.

    `end - 1` is shown before the wrap, and shown *explicitly*: playback drops
    the frames it could not decode (see `player.py`), so a clock that has
    already run past the end would otherwise skip the window's last frame on
    every lap — the one frame the user watching a behaviour end most needs to
    see. A target before the window is pulled forward to its start, which is
    what a playhead outside the window means when the window has just moved
    under it.
    """
    if target < window.start:
        return PlaybackStep(index=window.start, rewound=True)
    if target < window.end:
        return PlaybackStep(index=target, rewound=False)
    if current != window.end - 1:
        return PlaybackStep(index=window.end - 1, rewound=False)
    return PlaybackStep(index=window.start, rewound=True)
