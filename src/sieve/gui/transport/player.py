"""Playback and seek control on the GUI thread.

Three things make this more than a timer.

**Request coalescing.** At most one decode request is in flight and at most one
is pending, so a scrub that outruns the decoder discards the frames nobody
would have seen instead of queueing them. The discipline — the two slots, the
rank rule that keeps a released slider from being displaced by a later drag,
the display ordering, and the source stamp that stops a closed video's frame
being painted into the next one — lives in `RequestCoalescer`. What stays here
is everything that needs Qt or a decoder: the thread, the cache, the transport,
and the latency the policy below is fed.

**Adaptive coarse scrubbing.** Coalescing bounds how *far behind* a scrub can
fall; it does nothing about the cost of the one decode it still has to do, most
of which is an irreducible container seek. When sustained scrub latency exceeds
the budget the player snaps drag targets to a coarse grid and serves them from
`ProxyFrameCache`, which costs nothing because a cache hit does not seek. The
decision lives in `ScrubPolicy`; releasing the slider always decodes the exact
frame regardless of mode.

**A bounded transport.** Every position the player can reach is inside the
working window, and playback loops within it rather than running to the end of
the asset. The window arrives from the timeline bar through `set_window`, and
the arithmetic — which frame is shown last before the loop, and where a
playhead the window has moved out from under goes — is in `pacing.py`, because
it is off-by-one work and belongs somewhere a test can reach it without a
decode thread.

**Wall-clock playback.** Large footage does not decode at its own frame rate
and never will, so the player drives from elapsed wall time — target frame is
whatever the clock says it should be — and drops the frames it could not
decode. Playback runs at correct *speed* with a lower frame rate, which is what
a video editor does and what a user judging behaviour timing actually needs.
Playing every frame at the wrong speed would be the wrong tradeoff.
"""

from __future__ import annotations

from time import perf_counter

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QImage

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import METRICS, MetricBus
from sieve.core.pipeline_model import SourceSpan
from sieve.core.types import VideoMetadata
from sieve.gui.transport.coalescer import Request, RequestCoalescer
from sieve.gui.transport.decode_worker import DecodeWorker
from sieve.gui.transport.pacing import playback_step
from sieve.gui.transport.proxy_cache import ProxyFrameCache
from sieve.gui.transport.request_intent import RequestKind
from sieve.gui.transport.scrub_policy import ScrubPolicy
from sieve.mutual.shares import PROXY_CACHE_SHARE, resolved_bytes

#: How often playback re-evaluates which frame the clock is on. Finer than any
#: source frame rate we expect, so the limit on smoothness is decode, not this.
TICK_INTERVAL_MS = 8

#: Frame rate assumed when the container reports a nonsensical one.
FALLBACK_FPS = 30.0

#: The latency that defines "not keeping up", taken from the budget table so
#: the trigger and the documented ceiling cannot drift apart.
_SCRUB_BUDGET_MS = BUDGETS["scrub_to_repaint"].limit_ms


def _stop(thread: QThread) -> None:
    """Quit and join `thread`. Safe on one that has already finished."""
    thread.quit()
    thread.wait()


class VideoPlayer(QObject):
    """Owns the decode thread and the transport state for one video."""

    opened = Signal(VideoMetadata)
    failed = Signal(str)
    #: Index, picture, and why it was asked for. The third is what lets a
    #: subscriber decide what the frame is allowed to cost it —
    #: `request_intent.py` holds the predicates and the window reads
    #: `may_be_rendered`. Typed `object` because a `StrEnum` crossing a Qt
    #: signature declared `str` would arrive as one, and the member is the
    #: point. A subscriber that only paints connects a two-argument slot and Qt
    #: drops the rest, which is what `timeline/bar.py` does.
    frame_changed = Signal(int, QImage, object)
    playing_changed = Signal(bool)

    #: Emitted once per session, when sustained scrub latency has forced the
    #: player into coarse mode. The window owns the wording of the notice.
    scrub_degraded = Signal()

    _open_requested = Signal(str)
    _frame_requested = Signal(int)
    _close_requested = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        policy: ScrubPolicy | None = None,
        metrics: MetricBus | None = None,
    ) -> None:
        super().__init__(parent)

        self._metadata: VideoMetadata | None = None
        self._current_index = 0
        self._window: SourceSpan | None = None
        self._coalescer = RequestCoalescer()

        # Sized by the ledger, not by the class's own default: the share's
        # floor is that default, and the fraction lets a bigger allocation buy
        # more warmed grid points without a second number existing anywhere.
        self._cache = ProxyFrameCache(capacity_bytes=resolved_bytes(PROXY_CACHE_SHARE))
        # Injectable so the degradation path can be exercised against a
        # threshold a test can actually cross. On a machine fast enough to
        # meet the budget the default policy never degrades, which is correct
        # behaviour and useless as a test.
        self._policy = policy if policy is not None else ScrubPolicy(_SCRUB_BUDGET_MS)
        # Injectable for the reason above and for one more: a test that asserts
        # on what was published must not hear another test's player, and the
        # process-wide bus is shared by construction.
        self._metrics = METRICS if metrics is None else metrics

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
        self._close_requested.connect(self._worker.close)
        self._worker.opened.connect(self._on_opened)
        self._worker.failed.connect(self._on_failed)
        self._worker.frame_ready.connect(self._on_frame_ready)

        self._thread.start()

        # A running `QThread` whose wrapper is finalised aborts the process, so
        # stopping it cannot be left to a caller remembering to. `destroyed`
        # fires while the thread object is still valid and the closure holds
        # *it* rather than `self`, which is being torn down as the slot runs.
        # `shutdown` stays, and is what an orderly exit calls: this is the floor
        # under a player that is simply dropped.
        thread = self._thread
        self.destroyed.connect(lambda: _stop(thread))

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
    def window(self) -> SourceSpan | None:
        """The span the transport is confined to, or None for the whole asset."""
        return self._window

    @property
    def fps(self) -> float:
        """Effective frame rate, substituting a fallback for unusable metadata."""
        if self._metadata is None or self._metadata.fps <= 0:
            return FALLBACK_FPS
        return float(self._metadata.fps)

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

    def set_window(self, window: SourceSpan | None) -> None:
        """Confine the transport to `window`, or to the whole asset for None.

        The playhead follows. A window moved out from under it would otherwise
        leave the viewport showing a frame the transport can no longer reach,
        and the next play would jump somewhere the user did not ask to go — so
        the move is made visible immediately, at the frame nearest where they
        were.
        """
        self._window = window
        if self._metadata is None:
            return
        bounded = self._clamp(self._current_index)
        if bounded != self._current_index:
            self.seek(bounded)

    def seek(self, index: int) -> None:
        """Jump to exactly `index`, re-anchoring playback there if it is running.

        Clamped into the window, not merely into the source: a seek is how every
        caller reaches a frame, so this is the one place that has to hold for
        "the playhead is always inside the window" to be true. Reaching a frame
        outside it means moving the window first.
        """
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
        """Start playback. Rewinds to the window's start if parked on its last frame."""
        if self._metadata is None or self._playing:
            return
        window = self._bounds()
        if self._current_index >= window.end - 1:
            self._current_index = window.start
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
        """Advance to whatever frame the wall clock says we should be on.

        The window is what the clock is folded into: playback loops rather than
        stopping at the end, because the window is a span the user chose to
        watch repeatedly and pausing them at its last frame makes them press
        play once per viewing.
        """
        del event
        if not self._playing or self._metadata is None:
            return

        elapsed = perf_counter() - self._play_anchor_time
        target = self._play_anchor_index + int(elapsed * self.fps)
        step = playback_step(target, self._current_index, self._bounds())

        if step.rewound:
            self._anchor_playback(step.index)
        if step.index != self._current_index or self._coalescer.in_flight is not None:
            self._request(step.index, RequestKind.PLAYBACK)

    def _go_to(self, index: int, kind: RequestKind) -> None:
        if self._metadata is None:
            return
        index = self._clamp(index)
        self._anchor_playback(index)

        target = self._clamp(self._policy.snap(index)) if kind.may_be_snapped else index
        if self._display_cached(target, kind):
            return
        self._request(target, kind)

    def _display_cached(self, index: int, kind: RequestKind) -> bool:
        """Show a cached frame if we have one. This is the free path."""
        image = self._cache.get(index)
        if image is None:
            return False

        self._coalescer.served_without_decode(kind)
        self._current_index = index
        self.frame_changed.emit(index, image, kind)
        return True

    def _anchor_playback(self, index: int) -> None:
        self._play_anchor_time = perf_counter()
        self._play_anchor_index = index

    def _bounds(self) -> SourceSpan:
        """The window, or the whole asset when none has been set.

        A `SourceSpan` either way, so nothing downstream branches on the
        absence. The absence is a real state — the player is constructed before
        any video is open — and answering it with the asset's own span keeps the
        unbounded transport a special case of the bounded one rather than a
        second code path.
        """
        if self._window is not None:
            return self._window
        frames = self._metadata.frame_count if self._metadata is not None else 1
        return SourceSpan(start=0, end=max(frames, 1))

    def _clamp(self, index: int) -> int:
        if self._metadata is None:
            return 0
        window = self._bounds()
        return max(window.start, min(index, window.end - 1))

    def _reset_source_state(self) -> None:
        self._metadata = None
        self._current_index = 0
        self._window = None
        self._coalescer.new_generation()
        self._cache.clear()
        self._policy.reset()

    def _request(self, index: int, kind: RequestKind) -> None:
        """Ask the decode thread for a frame."""
        self._issue(self._coalescer.request(index, kind))

    def _issue(self, request: Request | None) -> None:
        """Send to the decode thread whatever the coalescer decided to issue."""
        if request is not None:
            self._frame_requested.emit(request.index)

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        self._metadata = metadata
        self._current_index = 0
        self._policy.set_fps(float(metadata.fps))
        self.opened.emit(metadata)
        self._request(0, RequestKind.EXACT)

    @Slot(int, QImage)
    def _on_frame_ready(self, index: int, image: QImage) -> None:
        arrival = self._coalescer.arrived()

        # A frame from a source we have closed or replaced. Not merely late:
        # showing it paints the old video into the new one's viewport, and
        # caching it would hand that frame back at the same index later. Drop
        # it whole — no display, no cache, no latency sample — but still drain,
        # because the slot it occupies is the new source's turn to use.
        if arrival.stale or arrival.request is None:
            self._issue(self._coalescer.drain())
            return

        if arrival.request.kind.may_be_retained:
            self._cache.put(index, image)

        if arrival.display:
            self._current_index = index
            self.frame_changed.emit(index, image, arrival.request.kind)

        # Measured after the emit so the synchronous view update counts. The
        # repaint itself is asynchronous and is not captured here.
        #
        # The same number goes two places and they are not the same question.
        # `ScrubPolicy` asks whether *this session* should degrade, which is a
        # decision with a hysteresis and a memory; the bus asks only what this
        # round trip cost, which is what `scrub_to_repaint` names and what a HUD
        # or a gate reads. Publishing the policy's verdict instead would give a
        # consumer the conclusion and not the measurement.
        if arrival.request.kind.is_felt_latency:
            round_trip_ms = self._coalescer.round_trip_ms()
            self._metrics.publish("scrub_to_repaint", round_trip_ms)
            if self._policy.observe(round_trip_ms):
                self.scrub_degraded.emit()

        self._issue(self._coalescer.drain())

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        # Draining here matters: a decode error that left the slot occupied
        # would wedge every later request behind it.
        self._issue(self._coalescer.drain())
        self.pause()
        self.failed.emit(message)
