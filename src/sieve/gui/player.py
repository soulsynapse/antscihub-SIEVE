"""Playback and seek control on the GUI thread.

Three things make this more than a timer.

**Request coalescing.** At most one decode request is in flight and at most one
is pending, so a scrub that outruns the decoder discards the frames nobody
would have seen instead of queueing them. The discipline — the two slots, the
rank rule that keeps a released slider from being displaced by a later drag,
the display ordering, and the source stamp that stops a closed video's frame
being painted into the next one — lives in `RequestCoalescer`, because
`pipeline/preview.py` needs the identical rules under the identical budget.
What stays here is everything that needs Qt or a decoder: the thread, the
cache, the transport, and the latency the policy below is fed.

**Adaptive coarse scrubbing.** Coalescing bounds how *far behind* a scrub can
fall; it does nothing about the cost of the one decode it still has to do. On
the reference source that is ~68 ms, most of it an irreducible container seek,
and on a slower machine it is worse. When sustained scrub latency exceeds the
budget the player snaps drag targets to a coarse grid and serves them from
`ProxyFrameCache`, which costs nothing because a cache hit does not seek. The
decision lives in `ScrubPolicy`; releasing the slider always decodes the exact
frame regardless of mode.

**A bounded transport.** Every position the player can reach is inside the
working window, and playback loops within it rather than running to the end of
the asset. That is what makes the window the unit of work VISION step 4 asks
for: the user picks the ten seconds that matter and the transport stops being
able to leave them. The window arrives from the document through `set_window`,
and the arithmetic — which frame is shown last before the loop, and where a
playhead the window has moved out from under goes — is in `timeline_model.py`,
because it is off-by-one work and belongs somewhere a test can reach it without
a decode thread.

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

from time import perf_counter

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QImage

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import METRICS, MetricBus
from sieve.core.pipeline_model import ClipRange
from sieve.core.types import VideoMetadata
from sieve.gui.coalescer import Request, RequestCoalescer, RequestKind
from sieve.gui.concurrency import PROXY_CACHE_SHARE, resolved_bytes
from sieve.gui.decode_worker import DecodeWorker
from sieve.gui.preferences import Preferences
from sieve.gui.proxy_cache import ProxyFrameCache
from sieve.gui.render_ring import RenderFrameRing
from sieve.gui.scrub_policy import ScrubPolicy
from sieve.gui.timeline_model import feed_bounds, playback_step

#: How often playback re-evaluates which frame the clock is on. Finer than any
#: source frame rate we expect, so the limit on smoothness is decode, not this.
TICK_INTERVAL_MS = 8

#: Frame rate assumed when the container reports a nonsensical one.
FALLBACK_FPS = 30.0

#: The latency that defines "not keeping up", taken from the budget table so
#: the trigger and the documented ceiling cannot drift apart.
_SCRUB_BUDGET_MS = BUDGETS["scrub_to_repaint"].limit_ms


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
    _luma_changed = Signal(bool)
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
        self._window: ClipRange | None = None
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
        self._playback_rate = 1.0
        self._tick_timer_id = 0

        self._thread = QThread()
        self._thread.setObjectName("sieve-decode")
        self._worker = DecodeWorker()
        self._worker.moveToThread(self._thread)

        self._viewport_luma = False

        # Render-fed playback: a ring of frames the render already decoded,
        # consulted before every decode of our own. The ring's frames are
        # luma, so `_viewport_luma` is part of the gate — the gray viewport
        # is what makes the render's format and ours the same format.
        self._render_ring: RenderFrameRing | None = None
        self._render_fed = True
        self._render_filling = False

        self._open_requested.connect(self._worker.open)
        self._frame_requested.connect(self._worker.request_frame)
        self._proxy_width_changed.connect(self._worker.set_proxy_width)
        self._luma_changed.connect(self._worker.set_luma)
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
    def window(self) -> ClipRange | None:
        """The span the transport is confined to, or None for the whole asset."""
        return self._window

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
        self._render_fed = preferences.render_fed_playback
        # Cached frames are proxies at the old width, so they are the wrong
        # size the moment the width changes and must not be served again. The
        # ring applies the same discipline internally on a width change.
        self._cache.clear()
        if self._render_ring is not None:
            self._render_ring.set_proxy_width(preferences.proxy_width)
        self._proxy_width_changed.emit(preferences.proxy_width)

    def set_render_feed(self, ring: RenderFrameRing | None) -> None:
        """Adopt `ring` as a source of frames that is not the decode thread.

        Called once at wiring time by whoever owns both the player and the
        render (`main_window.py`). The ring keeps its own lock; this object
        never mutates it beyond the width above.
        """
        self._render_ring = ring

    @Slot(bool)
    def set_render_filling(self, active: bool) -> None:
        """A window render started filling the ring, or stopped.

        While true and the feed is live, playback folds at the render's
        frontier rather than at the window's end — there is always something
        moving to watch, and it never runs ahead into frames whose only
        source would be the second decode this mode removes. When false the
        fold lifts; the ring is still consulted, because the frames it kept
        are still the frames.
        """
        self._render_filling = active

    @property
    def viewport_luma(self) -> bool:
        """Whether the viewport is currently being decoded grayscale."""
        return self._viewport_luma

    @property
    def playback_rate(self) -> float:
        """The transport's speed as a multiple of source time. 1.0 is real time."""
        return self._playback_rate

    def set_playback_rate(self, rate: float) -> None:
        """Play at `rate` times source speed.

        Still wall-clock playback — the module docstring's argument is
        unchanged, the clock is simply scaled — so frames the decoder cannot
        keep up with are dropped, not queued. Re-anchoring at the current
        frame is what makes the change take effect *from here*: the target
        arithmetic multiplies the whole elapsed span, and without a new
        anchor a rate change mid-play would teleport the playhead to where
        the new rate says it should have been all along.
        """
        if rate <= 0.0 or rate == self._playback_rate:
            return
        self._playback_rate = rate
        self._anchor_playback(self._current_index)

    def set_viewport_luma(self, enabled: bool) -> None:
        """Switch the viewport's decode format between colour and luma.

        Not part of `apply_preferences`, because the effective format is not
        the stored preference: the viewport toggle (`gui/gray_toggle.py`)
        folds the preference together with the render-in-progress policy and
        hands the answer here.

        Three things must happen with the flip, and the first two are the
        same discipline a source change follows. The cache is dropped — it is
        keyed by frame index and says nothing about format, so a cache warmed
        in colour would hand colour frames back into a gray viewport wherever
        the user happened to have scrubbed. The generation is bumped — a
        decode already in flight will come back in the old format, and the
        stamp is what stops it being painted or cached. And the frame on
        screen is re-requested at the new format, so the playhead survives
        the reopen and the pane never blanks.
        """
        if enabled == self._viewport_luma:
            return
        self._viewport_luma = enabled
        self._cache.clear()
        self._coalescer.new_generation()
        self._luma_changed.emit(enabled)
        if self._metadata is not None:
            self._request(self._current_index, RequestKind.EXACT)

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

    def set_window(self, window: ClipRange | None) -> None:
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
        target = self._play_anchor_index + int(elapsed * self.fps * self._playback_rate)
        bounds = self._bounds()
        ring = self._feed_ring()
        if ring is not None and self._render_filling:
            bounds = feed_bounds(bounds, ring.frontier)
        step = playback_step(target, self._current_index, bounds)

        if step.rewound:
            self._anchor_playback(step.index)
        if step.index != self._current_index or self._coalescer.in_flight is not None:
            self._request(step.index, RequestKind.PLAYBACK)

    def _go_to(self, index: int, kind: RequestKind) -> None:
        if self._metadata is None:
            return
        index = self._clamp(index)
        self._anchor_playback(index)

        target = self._clamp(self._policy.snap(index)) if kind is RequestKind.SCRUB else index
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
        self.frame_changed.emit(index, image)
        return True

    def _anchor_playback(self, index: int) -> None:
        self._play_anchor_time = perf_counter()
        self._play_anchor_index = index

    def _bounds(self) -> ClipRange:
        """The window, or the whole asset when none has been set.

        A `ClipRange` either way, so nothing downstream branches on the absence.
        The absence is a real state — the player is constructed before any
        document has a source — and answering it with the asset's own span keeps
        the unbounded transport a special case of the bounded one rather than a
        second code path.
        """
        if self._window is not None:
            return self._window
        frames = self._metadata.frame_count if self._metadata is not None else 1
        return ClipRange(start=0, end=max(frames, 1))

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

    def _feed_ring(self) -> RenderFrameRing | None:
        """The ring, when playback may take frames from it, else None.

        Three gates in one place: a ring must be wired, the preference must
        allow it, and the viewport must be gray — the ring's frames are luma,
        and serving one into a colour pane would be the format lie the
        gray-toggle item exists to prevent. The last gate is also what scopes
        the feed to the filter tab, since that tab is the only place the
        pane goes gray.
        """
        if self._render_fed and self._viewport_luma:
            return self._render_ring
        return None

    def _display_from_ring(self, index: int, kind: RequestKind) -> bool:
        """Show the render's frame if it kept one. The no-second-decode path.

        Deliberately not copied into `_cache`: the ring is its own retention,
        and playback frames are exactly what `gui/proxy_cache.py` says must
        not evict a scrub's warmed grid.
        """
        ring = self._feed_ring()
        if ring is None:
            return False
        image = ring.get(index)
        if image is None:
            return False
        self._coalescer.served_without_decode(kind)
        self._current_index = index
        self.frame_changed.emit(index, image)
        return True

    def _request(self, index: int, kind: RequestKind) -> None:
        """Ask the decode thread for a frame — unless the render already has it."""
        if self._display_from_ring(index, kind):
            return
        self._issue(self._coalescer.request(index, kind))

    def _issue(self, request: Request | None) -> None:
        """Send to the decode thread whatever the coalescer decided to issue."""
        if request is not None:
            self._frame_requested.emit(request.index)

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        self._metadata = metadata
        self._current_index = 0
        self._policy.set_fps(metadata.fps)
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

        if arrival.request.kind is not RequestKind.PLAYBACK:
            self._cache.put(index, image)

        if arrival.display:
            self._current_index = index
            self.frame_changed.emit(index, image)

        # Measured after the emit so the synchronous view update counts. The
        # repaint itself is asynchronous and is not captured here.
        #
        # The same number goes two places and they are not the same question.
        # `ScrubPolicy` asks whether *this session* should degrade, which is a
        # decision with a hysteresis and a memory; the bus asks only what this
        # round trip cost, which is what `scrub_to_repaint` names and what a HUD
        # or a gate reads. Publishing the policy's verdict instead would give a
        # consumer the conclusion and not the measurement.
        if arrival.request.kind is RequestKind.SCRUB:
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
