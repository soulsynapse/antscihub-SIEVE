"""Where playback goes next, and how far it may go while a render is filling.

Qt-free, like `coalescer.py` and `scrub_policy.py`, and for the same reason:
every rule here is wrong at the first or the last frame of a window before it
is right anywhere, and feeding these functions numbers is the whole test.

What a window *is* — how it moves, resizes, and clamps onto a source — is
`core/clip_window.py`, one layer down where the CLI can reach it. What is here
is the half of the old `gui/timeline_model.py` that only `player.py` consumes;
the frame-to-column mapping the band paints is `gui/timeline/geometry.py`. They
were one module until the two packages were drawn, at which point keeping them
together would have made `transport` and `timeline` import each other.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.core.pipeline_model import ClipRange


def feed_bounds(window: ClipRange, frontier: int | None) -> ClipRange:
    """What playback may cover while a render is filling: up to its frontier.

    Render-fed playback's fold. The player takes frames from the render's ring
    rather than decoding, so while the render is still producing, the last
    frame worth targeting is the last one that exists — playback loops over
    the rendered prefix while the window fills behind it, instead of running
    ahead into frames whose only source would be the second decode this mode
    exists to remove.

    `None` (nothing produced yet) and a frontier before the window (a stale
    claim from a window that has since moved) both yield the window unchanged:
    a fold that pinned playback to a single frame, or to a foreign span, would
    freeze the pane in the name of keeping it moving.
    """
    if frontier is None or frontier < window.start:
        return window
    return ClipRange(start=window.start, end=min(window.end, frontier + 1))


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


def playback_step(target: int, current: int, window: ClipRange) -> PlaybackStep:
    """Fold a wall-clock target into `[start, stop)`, looping at the end.

    `stop - 1` is shown before the wrap, and shown *explicitly*: playback drops
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
