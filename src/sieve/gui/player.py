"""Playback and seek control on the GUI thread.

Three things make this more than a timer.

**Request coalescing.** At most one decode request is in flight and at most one
is pending. A scrub that outruns the decoder therefore discards the frames
nobody would have seen instead of queueing them, so releasing the slider shows
the frame under the cursor rather than replaying the drag. This is what keeps
perceived scrub latency near the cost of one decode no matter how fast the
user moves.

Requests carry *why* they were made, which is what the single pending slot is
really for. A drag position is a guess the user is still refining and may be
snapped or dropped; the frame under a released slider is a commitment. Both
compete for the same slot, latest wins, but only the guesses are allowed to be
approximate — a pending exact request is never discarded in favour of a later
drag position, and only scrub round trips are timed for the degradation
decision below. Requests also carry *which source* they were made against,
because closing a video does not recall the decode already running against it;
the frame still arrives, and without that stamp it would be shown.

**Adaptive coarse scrubbing.** Coalescing bounds how *far behind* a scrub can
fall; it does nothing about the cost of the one decode it still has to do. On
the reference source that is ~68 ms, most of it an irreducible container seek,
and on a slower machine it is worse. When sustained scrub latency exceeds the
budget the player snaps drag targets to a coarse grid and serves them from
`FrameCache`, which costs nothing because a cache hit does not seek. The
decision lives in `ScrubPolicy`; releasing the slider always decodes the exact
frame regardless of mode.

**Wall-clock playback.** The reference source is 5312x2988 at 59.94 fps and
decodes at roughly 34 fps, so real-time playback is not achievable and never
will be for footage like this. The player therefore drives from elapsed wall
time — target frame is whatever the clock says it should be — and drops the
frames it could not decode. Playback runs at correct *speed* with a lower
frame rate, which is what a video editor does and what a user judging
behaviour timing actually needs. Playing every frame at the wrong speed would
be the wrong tradeoff.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from time import perf_counter

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QImage

from sieve.bench.budgets import BUDGETS
from sieve.core.types import VideoMetadata
from sieve.gui.decode_worker import DecodeWorker
from sieve.gui.frame_cache import FrameCache
from sieve.gui.preferences import Preferences
from sieve.gui.scrub_policy import ScrubPolicy

#: How often playback re-evaluates which frame the clock is on. Finer than any
#: source frame rate we expect, so the limit on smoothness is decode, not this.
TICK_INTERVAL_MS = 8

#: Frame rate assumed when the container reports a nonsensical one.
FALLBACK_FPS = 30.0

#: The latency that defines "not keeping up", taken from the budget table so
#: the trigger and the documented ceiling cannot drift apart.
_SCRUB_BUDGET_MS = BUDGETS["scrub_to_repaint"].limit_ms


class RequestKind(StrEnum):
    """Why a frame was asked for. Governs snapping, caching, and timing."""

    #: A committed position: a released slider, a step, a menu action. Must
    #: land on exactly this frame.
    EXACT = auto()
    #: A drag position. May be snapped to the coarse grid, and is the only
    #: kind whose latency counts toward the degradation decision.
    SCRUB = auto()
    #: Driven by the playback clock. Never snapped, never cached — playback
    #: walks the whole timeline and would evict everything a scrub warmed.
    PLAYBACK = auto()


@dataclass(frozen=True, slots=True)
class _Request:
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


class VideoPlayer(QObject):
    """Owns the decode thread and the transport state for one video."""

    opened = Signal(VideoMetadata)
    failed = Signal(str)
    frame_changed = Signal(int, QImage)
    playing_changed = Signal(bool)

    #: Emitted once per session, when sustained scrub latency has forced the
    #: player into coarse mode. The window owns the wording of the notice.
    scrub_degraded = Signal()

    _open_requested = Signal(str)
    _frame_requested = Signal(int)
    _proxy_width_changed = Signal(int)
    _close_requested = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        policy: ScrubPolicy | None = None,
    ) -> None:
        super().__init__(parent)

        self._metadata: VideoMetadata | None = None
        self._current_index = 0
        self._in_flight: _Request | None = None
        self._in_flight_at = 0.0
        self._pending: _Request | None = None

        # Monotonic display ordering. A cache hit can overtake an in-flight
        # decode, and the decode must not then repaint the older frame over it.
        self._sequence = 0
        self._displayed_sequence = 0

        # Which source requests are being made against. Bumped on every open
        # or close; a frame stamped with an older one is discarded on arrival.
        self._generation = 0

        self._cache = FrameCache()
        # Injectable so the degradation path can be exercised against a
        # threshold a test can actually cross. On a machine fast enough to
        # meet the budget the default policy never degrades, which is correct
        # behaviour and useless as a test.
        self._policy = policy if policy is not None else ScrubPolicy(_SCRUB_BUDGET_MS)

        self._playing = False
        self._play_anchor_time = 0.0
        self._play_anchor_index = 0
        self._tick_timer_id = 0

        self._thread = QThread()
        self._thread.setObjectName("sieve-decode")
        self._worker = DecodeWorker()
        self._worker.moveToThread(self._thread)

        self._open_requested.connect(self._worker.open)
        self._frame_requested.connect(self._worker.request_frame)
        self._proxy_width_changed.connect(self._worker.set_proxy_width)
        self._close_requested.connect(self._worker.close)
        self._worker.opened.connect(self._on_opened)
        self._worker.failed.connect(self._on_failed)
        self._worker.frame_ready.connect(self._on_frame_ready)

        self._thread.start()

    # ---- state -----------------------------------------------------------

    @property
    def metadata(self) -> VideoMetadata | None:
        """Metadata of the open video, or None when nothing is loaded."""
        return self._metadata

    @property
    def current_index(self) -> int:
        """Index of the most recently displayed frame."""
        return self._current_index

    @property
    def is_playing(self) -> bool:
        """Whether the transport is running."""
        return self._playing

    @property
    def is_scrub_degraded(self) -> bool:
        """Whether drag targets are currently being snapped to the coarse grid."""
        return self._policy.is_degraded

    @property
    def fps(self) -> float:
        """Effective frame rate, substituting a fallback for unusable metadata."""
        if self._metadata is None or self._metadata.fps <= 0.0:
            return FALLBACK_FPS
        return self._metadata.fps

    # ---- configuration ---------------------------------------------------

    def apply_preferences(self, preferences: Preferences) -> None:
        """Adopt the user's settings. Safe to call at any time."""
        self._policy.set_allow_degrade(preferences.adaptive_scrub)
        self._policy.set_coarse_interval_seconds(preferences.coarse_interval_seconds)
        # Cached frames are proxies at the old width, so they are the wrong
        # size the moment the width changes and must not be served again.
        self._cache.clear()
        self._proxy_width_changed.emit(preferences.proxy_width)

    # ---- transport -------------------------------------------------------

    def open(self, path: str) -> None:
        """Load a video. `opened` or `failed` follows."""
        self.pause()
        self._reset_source_state()
        self._open_requested.emit(path)

    def close(self) -> None:
        """Unload the current video."""
        self.pause()
        self._reset_source_state()
        self._close_requested.emit()

    def seek(self, index: int) -> None:
        """Jump to exactly `index`, re-anchoring playback there if it is running."""
        self._go_to(index, RequestKind.EXACT)

    def scrub(self, index: int) -> None:
        """Follow a drag to `index`.

        Approximate by permission: while the player is degraded this shows the
        nearest frame on the coarse grid instead. Call `seek` when the drag
        ends — that is what guarantees the user lands where they let go.
        """
        self._go_to(index, RequestKind.SCRUB)

    def step(self, delta: int) -> None:
        """Move `delta` frames from the current position. Pauses first."""
        self.pause()
        self.seek(self._current_index + delta)

    def play(self) -> None:
        """Start playback. Rewinds to the start if parked on the last frame."""
        if self._metadata is None or self._playing:
            return
        if self._current_index >= self._metadata.frame_count - 1:
            self._current_index = 0
        self._playing = True
        self._anchor_playback(self._current_index)
        self._tick_timer_id = self.startTimer(TICK_INTERVAL_MS)
        self.playing_changed.emit(True)

    def pause(self) -> None:
        """Stop playback. Safe to call when already paused."""
        if not self._playing:
            return
        self._playing = False
        if self._tick_timer_id:
            self.killTimer(self._tick_timer_id)
            self._tick_timer_id = 0
        self.playing_changed.emit(False)

    def toggle_play(self) -> None:
        """Play if paused, pause if playing."""
        if self._playing:
            self.pause()
        else:
            self.play()

    def shutdown(self) -> None:
        """Stop the decode thread. Call before the application exits."""
        self.pause()
        self._close_requested.emit()
        self._thread.quit()
        self._thread.wait()

    # ---- internals -------------------------------------------------------

    def timerEvent(self, event: object) -> None:
        """Advance to whatever frame the wall clock says we should be on."""
        del event
        if not self._playing or self._metadata is None:
            return

        elapsed = perf_counter() - self._play_anchor_time
        target = self._play_anchor_index + int(elapsed * self.fps)

        if target >= self._metadata.frame_count:
            self.pause()
            self._request(self._metadata.frame_count - 1, RequestKind.EXACT)
            return
        if target != self._current_index or self._in_flight is not None:
            self._request(target, RequestKind.PLAYBACK)

    def _go_to(self, index: int, kind: RequestKind) -> None:
        if self._metadata is None:
            return
        index = self._clamp(index)
        self._anchor_playback(index)

        target = self._clamp(self._policy.snap(index)) if kind is RequestKind.SCRUB else index
        if self._display_cached(target, supersedes_scrub=kind is RequestKind.SCRUB):
            return
        self._request(target, kind)

    def _display_cached(self, index: int, *, supersedes_scrub: bool) -> bool:
        """Show a cached frame if we have one. This is the free path."""
        image = self._cache.get(index)
        if image is None:
            return False

        # A pending drag position is now stale — we have shown something the
        # user asked for more recently. A pending exact request is a
        # commitment and survives.
        if (
            supersedes_scrub
            and self._pending is not None
            and self._pending.kind is RequestKind.SCRUB
        ):
            self._pending = None

        self._sequence += 1
        self._displayed_sequence = self._sequence
        self._current_index = index
        self.frame_changed.emit(index, image)
        return True

    def _anchor_playback(self, index: int) -> None:
        self._play_anchor_time = perf_counter()
        self._play_anchor_index = index

    def _clamp(self, index: int) -> int:
        if self._metadata is None:
            return 0
        return max(0, min(index, self._metadata.frame_count - 1))

    def _reset_source_state(self) -> None:
        self._metadata = None
        self._current_index = 0
        self._generation += 1
        # `_in_flight` deliberately survives. The decode thread is already
        # working on it and will emit `frame_ready` regardless; leaving the
        # slot occupied is what keeps "one outstanding decode" and "in flight
        # is not None" the same statement, so `_drain` still issues the new
        # source's first request at the right moment. The generation stamp,
        # not a cleared slot, is what stops the frame being shown.
        self._pending = None
        self._cache.clear()
        self._policy.reset()

    def _request(self, index: int, kind: RequestKind) -> None:
        """Ask the decode thread for a frame, coalescing against any in flight."""
        self._sequence += 1
        request = _Request(
            index=index,
            kind=kind,
            sequence=self._sequence,
            generation=self._generation,
        )
        if self._in_flight is not None:
            self._pending = request
            return
        self._issue(request)

    def _issue(self, request: _Request) -> None:
        self._in_flight = request
        # Timed from issue, not from creation: a request that waited its turn
        # in the pending slot did not take that long to decode, and charging
        # it the wait would degrade the player for being busy.
        self._in_flight_at = perf_counter()
        self._frame_requested.emit(request.index)

    def _drain(self) -> None:
        self._in_flight = None
        if self._pending is not None:
            request, self._pending = self._pending, None
            self._issue(request)

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        self._metadata = metadata
        self._current_index = 0
        self._policy.set_fps(metadata.fps)
        self.opened.emit(metadata)
        self._request(0, RequestKind.EXACT)

    @Slot(int, QImage)
    def _on_frame_ready(self, index: int, image: QImage) -> None:
        request = self._in_flight

        # A frame from a source we have closed or replaced. Not merely late:
        # showing it paints the old video into the new one's viewport, and
        # caching it would hand that frame back at the same index later. Drop
        # it whole — no display, no cache, no latency sample — but still drain,
        # because the slot it occupies is the new source's turn to use.
        if request is None or request.generation != self._generation:
            self._drain()
            return

        if request.kind is not RequestKind.PLAYBACK:
            self._cache.put(index, image)

        # Suppress a decode that a cache hit has already overtaken; repainting
        # it would move the viewport backwards under the user's cursor. An
        # exact request is exempt: it is a position the user committed to, and
        # dropping it because a drag position arrived first strands them on a
        # grid point they never asked for.
        display = request.kind is RequestKind.EXACT or request.sequence > self._displayed_sequence
        self._displayed_sequence = max(self._displayed_sequence, request.sequence)

        if display:
            self._current_index = index
            self.frame_changed.emit(index, image)

        # Measured after the emit so the synchronous view update counts. The
        # repaint itself is asynchronous and is not captured here.
        elapsed_ms = (perf_counter() - self._in_flight_at) * 1000.0
        if request.kind is RequestKind.SCRUB and self._policy.observe(elapsed_ms):
            self.scrub_degraded.emit()

        self._drain()

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        # Clearing in-flight here matters: a decode error that left the slot
        # occupied would wedge every later request behind it.
        self._drain()
        self.pause()
        self.failed.emit(message)
