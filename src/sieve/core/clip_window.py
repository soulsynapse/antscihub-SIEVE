"""What survives an edit to a `ClipRange`: its length, or one of its edges.

`ROI` carries its own algebra on `core/types.py` — `clamped_to`, `resized_in` —
because a box trimmed onto a frame is a claim about the saved artifact and not
about the widget that dragged it. This is the same algebra for the other saved
geometry, and it lived under `gui/` until 2026-08-04 for no reason but the
order things were built in. A clamp that only the GUI can reach is one the CLI
does without: `cli/common.span_for` hands back `project.clip` verbatim, so a
project whose saved span outruns the video actually bound runs a span that is
partly not there, where the GUI shows the honest `None`.

Every rule here is wrong at the first or the last frame of a video before it is
wrong anywhere else, and a rule written inline in a `paintEvent` is one whose
failure is a band a few pixels off rather than a red test. Feeding these
functions numbers is the whole test.

**The window holds a length and moves an origin.** `ClipRange` stores
`(start, end)`, which carries the same information as `(start, length)`; what
is stored is not the question. The question is which one survives an edit, and
the answer is the length: the user's gesture is "keep the ten seconds, move
them", and two independent marks cannot express it — an in point dragged past
the out point has to invent a new out point, and whatever it invents is a span
nobody asked for. `started_at` and `ended_at_handle` are the one gesture that
*is* two marks — a bracket handle held under the cursor — and they carry a
floor for exactly the reason the keystroke marks do not need one: the invented
span is what a drag would produce continuously on the way past zero.
"""

from __future__ import annotations

from sieve.core.pipeline_model import ClipRange

#: How long a window is when nobody has chosen one. VISION step 4 asks the user
#: to tune against five to ten seconds; ten is the generous end, because a
#: window that is too long is trimmed by watching it and one that is too short
#: hides the behaviour the user opened the file to find.
DEFAULT_WINDOW_SECONDS = 10.0


def default_window(frame_count: int, fps: float) -> ClipRange | None:
    """The window a session opens with: `DEFAULT_WINDOW_SECONDS`, or all of it.

    `None` when there is no source. A non-positive `fps` yields the whole asset
    rather than a guessed frame count — the container has not said how long ten
    seconds is, and inventing a number here would put the user in a window whose
    length means nothing.
    """
    if frame_count <= 0:
        return None
    if fps <= 0.0:
        return ClipRange(start=0, end=frame_count)
    length = min(max(round(DEFAULT_WINDOW_SECONDS * fps), 1), frame_count)
    return ClipRange(start=0, end=length)


def effective_window(clip: ClipRange | None, frame_count: int, fps: float) -> ClipRange | None:
    """What a session shows: the user's choice, or the default until they make one.

    The absence is preserved rather than resolved, which is the whole point of
    routing every read through here. `Project.clip = None` means "the whole
    video" to `pipeline/plan.py` and "not chosen yet" to the document, and
    neither statement survives a caller that writes ten seconds into the project
    on open just so it has something to paint. Derived on every read, so there
    is one stored window and no second copy to drift from it.
    """
    if clip is None:
        return default_window(frame_count, fps)
    return clip


def moved_to(window: ClipRange, origin: int, frame_count: int) -> ClipRange:
    """`window` starting at `origin`, holding its length, clamped to the source.

    The clamp moves the window rather than shortening it, so a window dragged
    off the end of the source comes to rest against it at full length. Shrinking
    instead would mean the user got a shorter span for having gone too far, and
    they would have no way to tell it had happened except by reading the length
    back.
    """
    length = min(window.frame_count, frame_count)
    start = min(max(origin, 0), frame_count - length)
    return ClipRange(start=start, end=start + length)


def containing(window: ClipRange, frame: int, frame_count: int) -> ClipRange:
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


def ended_at(window: ClipRange | None, frame: int, frame_count: int) -> ClipRange:
    """`window` ending after `frame`, inclusive of it. This is the resize.

    The mirror of `moved_to`: an origin move holds the length, and an end mark
    sets it. An end at or before the origin sends the origin back to the head of
    the source — the user has decisively left the old span, so it is the
    *origin* that is stale, and refusing the mark would be a keystroke that does
    nothing and says nothing.
    """
    end = min(max(frame, 0), frame_count - 1) + 1
    start = 0
    if window is not None and window.start < end:
        start = window.start
    return ClipRange(start=start, end=end)


def started_at(window: ClipRange, frame: int, frame_count: int, floor: int) -> ClipRange:
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
    return ClipRange(start=min(max(frame, 0), end - limit), end=end)


def ended_at_handle(window: ClipRange, frame: int, frame_count: int, floor: int) -> ClipRange:
    """`window` with its end dragged past `frame`, its start pinned. The right handle.

    The mirror of `started_at`, and deliberately *not* `ended_at`: an out point
    marked before the origin releases the origin to the head of the source,
    because a keystroke that does nothing says nothing. A handle drag says
    something continuously — the bracket is under the cursor — so the same input
    means "as short as you are allowed", not "start over from zero".
    """
    limit = min(max(floor, 1), frame_count)
    start = min(max(window.start, 0), frame_count - limit)
    return ClipRange(start=start, end=min(max(frame + 1, start + limit), frame_count))


def fitted(window: ClipRange | None, frame_count: int) -> ClipRange | None:
    """A window trimmed onto a source of `frame_count` frames, or `None`.

    `None` out of a window that lands entirely past the end is a different
    statement from `None` in, and both are honest: it covers no frame of the
    video that is open, which is where a user sits before choosing anything.
    Clamping it to the last frame would hand back a one-frame window nobody
    marked.
    """
    if window is None or frame_count <= 0 or window.start >= frame_count:
        return None
    return ClipRange(start=window.start, end=min(window.end, frame_count))
