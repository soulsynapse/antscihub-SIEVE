"""The arithmetic behind the timeline: where a frame lands, and where the window goes.

Qt-free, like `gui/coalescer.py` and `gui/scrub_policy.py`, and for the same
reason. Every rule here is wrong at the first or the last frame of a video
before it is right anywhere, and a rule written inline in a `paintEvent` is one
whose failure is a band a few pixels off rather than a red test. Feeding these
functions numbers is the whole test.

Three separate things live here and they are separate on purpose.

**The mapping** (`Geometry`) turns a frame index into a column and back. The
band spans the whole asset with no handle to make room for, so it is
proportional — `frame / frame_count * width` — and not the groove-less-handle
arithmetic the old `ClipSlider` needed. A frame owns the *column* starting at
`x_of_frame`, which is why a span's right edge is `x_of_frame(end)` and not
`x_of_frame(end - 1)`: the window runs up to the start of the frame after its
last, so a one-frame window is one column wide instead of zero.

**The window rules** hold a length and move an origin. `ClipRange` stores
`(start, end)`, which carries the same information as `(start, length)`; what
is stored is not the question. The question is which one survives an edit, and
the answer is the length: the user's gesture is "keep the ten seconds, move
them", and two independent marks cannot express it — an in point dragged past
the out point has to invent a new out point, and whatever it invents is a span
nobody asked for. `started_at` and `ended_at_handle` are the one gesture that
*is* two marks — a bracket handle held under the cursor — and they carry a
floor for exactly the reason the keystroke marks do not need one: the invented
span is what a drag would produce continuously on the way past zero.

**The playback rule** wraps at the window's end. It is here rather than in
`player.py` because "the last frame shown before looping is `stop - 1`" is an
off-by-one claim, and off-by-one claims belong somewhere a test can state them
without a decode thread.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.core.pipeline_model import ClipRange

#: How long a window is when nobody has chosen one. Ten seconds avoids
#: accidentally selecting too little context because a
#: window that is too long is trimmed by watching it and one that is too short
#: hides the behaviour the user opened the file to find.
DEFAULT_WINDOW_SECONDS = 10.0

#: Narrowest a painted span may be. A window of one frame in a two-hour source
#: is a fraction of a pixel, and a band nobody can see reads as no band at all —
#: which is the same failure as painting the wrong span, arriving through the
#: width instead of through the position.
MIN_BAND_PIXELS = 2.0


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
    """What the timeline shows: the user's choice, or the default until they make one.

    The absence is preserved rather than resolved, which is the whole point of
    routing every read through here. `Project.clip = None` means "the whole
    video" to `pipeline/plan.py` and "not chosen yet" to the document, and
    neither statement survives a GUI that writes ten seconds into the document
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

    `None` out of a window that lands entirely past the end is the same claim
    `ReplicateDocument._fit_clip` makes about a saved span: it covers no frame
    of the video that is open, which is where a user sits before choosing
    anything. Clamping it to the last frame would hand back a one-frame window
    nobody marked.
    """
    if window is None or frame_count <= 0 or window.start >= frame_count:
        return None
    return ClipRange(start=window.start, end=min(window.end, frame_count))


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


@dataclass(frozen=True, slots=True)
class Geometry:
    """The frame↔column mapping for a band `width` pixels wide over `frame_count`.

    Constructed per paint and per click rather than held, because both of its
    fields change under the user: a resized window changes the width and an
    opened video changes the count, and a cached mapping is one that paints the
    previous video's proportions until something invalidates it.
    """

    frame_count: int
    width: float

    @property
    def is_empty(self) -> bool:
        """Whether there is anything to map. Nothing is drawn or hit-tested if so."""
        return self.frame_count <= 0 or self.width <= 0.0

    def x_of_frame(self, frame: int) -> float:
        """Left edge of the column `frame` occupies.

        Accepts `frame_count` itself, which is not a frame: it is where the
        asset ends, and a half-open span's right edge lands on it.
        """
        if self.is_empty:
            return 0.0
        bounded = min(max(frame, 0), self.frame_count)
        return bounded / self.frame_count * self.width

    def centre_of_frame(self, frame: int) -> float:
        """Middle of the column `frame` occupies — where the playhead is drawn.

        The playhead is a claim about one frame, and one frame is a column, not
        a boundary. Drawn at the left edge it sits between two frames and reads
        as pointing at the earlier one at the end of a scrub.
        """
        if self.is_empty:
            return 0.0
        bounded = min(max(frame, 0), self.frame_count - 1)
        return (bounded + 0.5) / self.frame_count * self.width

    def span(self, start: int, end: int) -> tuple[float, float]:
        """Left and right edges of the half-open span `[start, end)`, in pixels.

        Never narrower than `MIN_BAND_PIXELS`, and widened rightward from the
        left edge so the span's *position* stays true when its width is being
        rounded up.
        """
        left = self.x_of_frame(start)
        right = max(self.x_of_frame(end), left + MIN_BAND_PIXELS)
        return left, right

    def frame_at(self, x: float) -> int:
        """The frame whose column contains `x`, clamped to the asset.

        The inverse of `x_of_frame` over the full width, not `width - 1`. The
        off-by-one version reaches the last frame a pixel early and never
        reaches it at all when the band is wider than the asset is long, which
        is the ordinary case for a short clip in a maximised window.
        """
        if self.is_empty:
            return 0
        index = int(x / self.width * self.frame_count)
        return min(max(index, 0), self.frame_count - 1)
