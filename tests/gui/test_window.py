"""The window algebra fed numbers, which its own module docstring calls the test.

`test_timeline.py` reaches these functions through the bar's gestures, and every
window the bar can hold is one the bar derived from the source it is showing —
`whole_of` is the source's own length, `set_window_length` clamps to it, and both
handle drags clamp to it — so `moved_to`'s length clamp never bites there. The
input it is written for is a window longer than its source, and the bar has no
gesture that produces one
(`findings/2026.08.08-no-gesture-hands-the-window-algebra-a-span-longer-than-its-source.md`).

So this is a claim about the function's contract and not about a path through the
widget: a caller that hands `moved_to` a window the source cannot hold gets the
source, not a span that starts before frame zero.

`window.py` imports nothing from Qt, so nothing here asks for a `QApplication`;
the import stays inside the body for the convention `conftest.py` gives.
"""

from __future__ import annotations

from sieve.core.pipeline_model import SourceSpan

#: Shorter than the window below, which is the whole of the proportion.
SOURCE_FRAMES = 12


def test_a_window_longer_than_its_source_comes_to_rest_over_the_whole_of_it() -> None:
    """The length is what the source can hold, not what the window arrived with.

    Without the clamp the failure is not a misplaced window: `start` is pinned to
    `frame_count - length`, which goes negative the moment the window is the
    longer of the two, and `SourceSpan` refuses a negative start. So the caller
    that asked to move a too-long window gets an exception out of a function
    whose whole job is to return a window it can draw.
    """
    from sieve.gui.timeline.window import moved_to

    too_long = SourceSpan(start=0, end=SOURCE_FRAMES + 8)

    moved = moved_to(too_long, 5, SOURCE_FRAMES)

    assert moved == SourceSpan(start=0, end=SOURCE_FRAMES)
