"""What survives an edit to the working window: its length, or one of its edges.

Every rule here is wrong at the first or the last frame of a video before it is
wrong anywhere else, and a rule written inline in a `paintEvent` is one whose
failure is a band a few pixels off rather than a red test. Feeding these
functions numbers is the whole test.

**The window holds a length and moves an origin.** `SourceSpan` stores
`(start, end)`, which carries the same information as `(start, length)`; what is
stored is not the question. The question is which one survives an edit, and the
answer is the length: the user's gesture is "keep the ten seconds, move them",
and two independent marks cannot express it — an in point dragged past the out
point has to invent a new out point, and whatever it invents is a span nobody
asked for. `started_at` and `ended_at` are the one gesture that *is* two marks —
a bracket handle held under the cursor — and they carry a floor for exactly that
reason: the invented span is what a drag would produce continuously on the way
past zero.

Under `gui/` and not `core/` because in v3 no headless caller has a window. v2
kept the algebra in `core` so the CLI could clamp the span saved on the project;
schema v1 saves none, and what a run covers is the `span` node's parameters.
"""

from __future__ import annotations

from sieve.core.pipeline_model import SourceSpan


def whole_of(frame_count: int) -> SourceSpan | None:
    """The window a source opens with: all of it, or `None` when there is none.

    All of it, and not v2's ten seconds. That default existed to propose the
    tuning span that got saved into the project, and schema v1 saves none — so a
    shorter opening window here would be a bound on what the user can watch,
    proposed by nothing and undoable only by dragging it back out.
    """
    if frame_count <= 0:
        return None
    return SourceSpan(start=0, end=frame_count)


def moved_to(window: SourceSpan, origin: int, frame_count: int) -> SourceSpan:
    """`window` starting at `origin`, holding its length, clamped to the source.

    The clamp moves the window rather than shortening it, so a window dragged
    off the end of the source comes to rest against it at full length. Shrinking
    instead would mean the user got a shorter span for having gone too far, and
    they would have no way to tell it had happened except by reading the length
    back.
    """
    length = min(window.frame_count, frame_count)
    start = min(max(origin, 0), frame_count - length)
    return SourceSpan(start=start, end=start + length)


def containing(window: SourceSpan, frame: int, frame_count: int) -> SourceSpan:
    """`window` moved the least distance that puts `frame` inside it.

    A click inside the window is a seek and never reaches this; a click outside
    is "take me there", and the smallest honest reading of that is to bring the
    window to the frame rather than to centre it on it. Centring would move the
    window twice as far as asked and lose the stretch the user was looking at.
    """
    if window.start <= frame < window.end:
        return window
    origin = frame if frame < window.start else frame - window.frame_count + 1
    return moved_to(window, origin, frame_count)


def started_at(window: SourceSpan, frame: int, frame_count: int, floor: int) -> SourceSpan:
    """`window` with its start dragged to `frame`, its end pinned. The left handle.

    Not `moved_to`, which is the *body* drag: a handle moves one edge and the
    other must not travel, or the user resizing from the left would watch the
    right edge slide away from the frame they were holding it against.

    `floor` is the shortest window a drag may produce. A drag past it stops
    there rather than being refused outright — a handle that goes dead under the
    cursor reads as a broken widget, where one that stops reads as a limit. A
    source shorter than `floor` is its own floor.
    """
    limit = min(max(floor, 1), frame_count)
    end = min(max(window.end, limit), frame_count)
    return SourceSpan(start=min(max(frame, 0), end - limit), end=end)


def ended_at(window: SourceSpan, frame: int, frame_count: int, floor: int) -> SourceSpan:
    """`window` with its end dragged past `frame`, its start pinned. The right handle.

    The mirror of `started_at`. A handle dragged back past its own start means
    "as short as you are allowed" and not "start over from zero": the bracket is
    under the cursor and says something continuously, so an input that produced
    a window at the head of the source would teleport the thing being held.
    """
    limit = min(max(floor, 1), frame_count)
    start = min(max(window.start, 0), frame_count - limit)
    return SourceSpan(start=start, end=min(max(frame + 1, start + limit), frame_count))
