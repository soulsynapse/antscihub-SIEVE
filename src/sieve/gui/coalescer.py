"""One frame request in flight, one waiting, everything between discarded.

This is the ordering discipline that makes a scrub feel bounded. Measured, a
burst of 40 seeks settles on the final target in ~172 ms — two decodes — where
queueing the same burst takes ~3.2 s and paints 38 frames nobody asked for. The player holds
the scrub budget by discarding work, not by decoding faster.

`pipeline/preview.py` needs the identical discipline against filtered frames
under the same 100 ms ceiling, which is why this is not a private detail of
`VideoPlayer` any more: two copies of a cross-thread ordering rule diverge on
exactly the behaviour the budget table pins, and the divergence shows up as a
viewport that stutters rather than as a failing test. Qt-free like
`ScrubPolicy`, and for the same reason — the properties worth pinning are
orderings, and orderings are tested by feeding them numbers.

Four rules, and they are the whole object:

**One in flight, one pending.** A third request overwrites the second. The
decode already running cannot be recalled, so two slots is the floor.

**A commitment outranks a guess.** Requests carry *why* they were made. A drag
position is a guess the user is still refining; a released slider, a step, or a
menu action is a commitment to land on exactly that frame. Where they compete
for the one pending slot the commitment wins regardless of arrival order —
otherwise a playback tick or a fresh drag silently strands the user somewhere
they never asked to be. Between requests of equal rank, later wins.

**Displays are monotonic.** A frame served from a cache can overtake a decode
that is still running, and that decode must not then repaint the older frame
over it. A commitment is exempt: it is exact by definition, and dropping it
because a guess arrived first is the same stranding as above.

**A frame outlives the source it was asked for.** Closing a video does not
recall the decode running against it. The frame still arrives, and without a
stamp saying which source it answers it would be painted into the next video's
viewport and cached there. `generation` is that stamp.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum, auto
from time import perf_counter


class RequestKind(StrEnum):
    """Why a frame was asked for. Governs rank, snapping, caching, and timing."""

    #: A committed position: a released slider, a step, a menu action. Must
    #: land on exactly this frame. The only kind that outranks another.
    EXACT = auto()
    #: A drag position. May be snapped to a coarse grid by the caller, and is
    #: the only kind whose latency counts toward the degradation decision.
    SCRUB = auto()
    #: Driven by the playback clock. Never snapped, never cached — playback
    #: walks the whole timeline and would evict everything a scrub warmed.
    PLAYBACK = auto()


@dataclass(frozen=True, slots=True)
class Request:
    """One decode request.

    `sequence` orders displays within a source, not decodes. `generation`
    identifies the source: it says which video the request was made against,
    which `sequence` cannot, because a frame from the previous video is not
    late — it is answering a question nobody is asking any more.
    """

    index: int
    kind: RequestKind
    sequence: int
    generation: int


@dataclass(frozen=True, slots=True)
class Arrival:
    """What to do with a frame that has just come back.

    `stale` and `display` are separate answers. A stale frame is dropped whole
    — no display, no cache, no latency sample — while a merely superseded one
    is still a frame of the current source and worth caching even though
    painting it would move the viewport backwards.
    """

    #: The request this frame answers, or None if nothing was in flight.
    request: Request | None
    #: Whether to paint it.
    display: bool
    #: Whether it answers a source that has since been closed or replaced.
    stale: bool


def _outranks(kind: RequestKind, pending: Request) -> bool:
    """Whether a new intent of `kind` may take the pending slot from `pending`."""
    return pending.kind is not RequestKind.EXACT or kind is RequestKind.EXACT


class RequestCoalescer:
    """The two slots, the sequence counters, and the generation stamp.

    Knows nothing about what a frame is, where it comes from, or how long a
    decode is allowed to take. It decides *which* request is outstanding and
    *whether* an answer is worth painting; caching, snapping, and the latency
    budget belong to the caller.

    Two calls make one arrival: `arrived` gives the verdict and `drain` frees
    the slot and hands back the next request to issue. They are separate so the
    caller can paint, and time the round trip against the repaint it just did,
    before the next decode's clock starts.
    """

    def __init__(self, *, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock
        self._in_flight: Request | None = None
        self._issued_at = 0.0
        self._pending: Request | None = None

        # Monotonic display ordering. A frame the caller served itself can
        # overtake an in-flight decode, and the decode must not repaint over it.
        self._sequence = 0
        self._displayed_sequence = 0

        # Which source requests are being made against. Neither counter above
        # is reset when this changes: display order is a property of the
        # session, and reusing sequence numbers across sources would make an
        # old frame look current.
        self._generation = 0

    # ---- state -----------------------------------------------------------

    @property
    def in_flight(self) -> Request | None:
        """The request being decoded right now, if any."""
        return self._in_flight

    @property
    def pending(self) -> Request | None:
        """The request that will be issued when the current one lands, if any."""
        return self._pending

    @property
    def generation(self) -> int:
        """Which source requests are currently being stamped with."""
        return self._generation

    # ---- intents ---------------------------------------------------------

    def request(self, index: int, kind: RequestKind) -> Request | None:
        """Ask for a frame.

        Returns the request to issue now, or None — either because something is
        already in flight and this one took the pending slot, or because it was
        dropped for outranking: a guess never displaces a commitment.
        """
        if self._in_flight is None:
            return self._issue(self._stamp(index, kind))
        if self._pending is not None and not _outranks(kind, self._pending):
            return None
        self._pending = self._stamp(index, kind)
        return None

    def served_without_decode(self, kind: RequestKind) -> None:
        """Record a frame the caller displayed itself, with no decode at all.

        A cache hit is the reason this exists. It has to enter the sequence, or
        an in-flight decode issued before it would still be judged newer and
        repaint over it. It also makes a pending request stale under the same
        rank rule the pending slot follows — the user has been shown something
        they asked for more recently.
        """
        self._sequence += 1
        self._displayed_sequence = self._sequence
        if self._pending is not None and _outranks(kind, self._pending):
            self._pending = None

    def new_generation(self) -> None:
        """Note that the source has changed.

        `in_flight` deliberately survives. The decode thread is already working
        on it and will answer regardless; leaving the slot occupied is what
        keeps "one outstanding decode" and "in flight is not None" the same
        statement, so `drain` still issues the new source's first request at the
        right moment. The stamp, not a cleared slot, is what stops the frame
        being shown.
        """
        self._generation += 1
        self._pending = None

    # ---- answers ---------------------------------------------------------

    def arrived(self) -> Arrival:
        """Judge the frame that just came back. Follow with `drain`."""
        request = self._in_flight
        if request is None or request.generation != self._generation:
            return Arrival(request=request, display=False, stale=True)

        display = request.kind is RequestKind.EXACT or request.sequence > self._displayed_sequence
        self._displayed_sequence = max(self._displayed_sequence, request.sequence)
        return Arrival(request=request, display=display, stale=False)

    def round_trip_ms(self) -> float:
        """How long the in-flight request has taken, in milliseconds.

        Timed from issue, not from creation: a request that waited its turn in
        the pending slot did not take that long to decode, and charging it the
        wait would penalise the caller for being busy. Valid until `drain`.
        """
        return (self._clock() - self._issued_at) * 1000.0

    def drain(self) -> Request | None:
        """Free the slot and hand back the next request to issue, if any.

        Must be called for every arrival, including a stale one and a failure:
        the slot a dropped frame occupies is the next source's turn to use, and
        a decode error that left it occupied would wedge everything behind it.
        """
        self._in_flight = None
        if self._pending is None:
            return None
        request, self._pending = self._pending, None
        return self._issue(request)

    # ---- internals -------------------------------------------------------

    def _stamp(self, index: int, kind: RequestKind) -> Request:
        self._sequence += 1
        return Request(
            index=index,
            kind=kind,
            sequence=self._sequence,
            generation=self._generation,
        )

    def _issue(self, request: Request) -> Request:
        self._in_flight = request
        self._issued_at = self._clock()
        return request
