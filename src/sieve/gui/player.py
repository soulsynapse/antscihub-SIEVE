from __future__ import annotations

from time import perf_counter

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtGui import QImage

from sieve.bench.budgets import BUDGETS
from sieve.bench.metrics import METRICS, MetricBus
from sieve.bench.retention_trace import (
    FROM_CACHE,
    FROM_DECODE,
    FROM_RING,
    GET,
    TRACE,
    AccessEvent,
    TraceRecorder,
)
from sieve.core.pipeline_model import ClipRange
from sieve.core.pool_meter import PoolMeter
from sieve.core.shares import PROXY_CACHE_SHARE, resolved_bytes
from sieve.core.types import VideoMetadata
from sieve.gui.coalescer import Request, RequestCoalescer, RequestKind
from sieve.gui.decode_worker import DecodeWorker
from sieve.gui.preferences import Preferences
from sieve.gui.proxy_cache import ProxyFrameCache
from sieve.gui.render_ring import RenderFrameRing
from sieve.gui.scrub_policy import ScrubPolicy
from sieve.gui.timeline_model import feed_bounds, playback_step


TICK_INTERVAL_MS = 8


FALLBACK_FPS = 30.0


_SCRUB_BUDGET_MS = BUDGETS["scrub_to_repaint"].limit_ms


class VideoPlayer(QObject):
    opened = Signal(VideoMetadata)
    failed = Signal(str)
    frame_changed = Signal(int, QImage)
    playing_changed = Signal(bool)

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
        trace: TraceRecorder | None = None,
    ) -> None:
        super().__init__(parent)
        self._metadata: VideoMetadata | None = None
        self._current_index = 0
        self._window: ClipRange | None = None
        self._coalescer = RequestCoalescer()
        self._cache = ProxyFrameCache(capacity_bytes=resolved_bytes(PROXY_CACHE_SHARE))
        self._policy = policy if policy is not None else ScrubPolicy(_SCRUB_BUDGET_MS)
        self._metrics = METRICS if metrics is None else metrics
        self._trace = TRACE if trace is None else trace
        self._playing = False
        self._play_anchor_time = 0.0
        self._play_anchor_index = 0
        self._playback_rate = 1.0
        self._tick_timer_id = 0
        self._thread = QThread()
        self._thread.setObjectName("sieve-decode")
        self._decode_meter = PoolMeter()
        self._worker = DecodeWorker(self._decode_meter)
        self._worker.moveToThread(self._thread)
        self._viewport_luma = False
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

    @property
    def metadata(self) -> VideoMetadata | None:
        return self._metadata

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def decode_meter(self) -> PoolMeter:
        return self._decode_meter

    @property
    def render_fed(self) -> bool:
        return self._feed_ring() is not None

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def is_scrub_degraded(self) -> bool:
        return self._policy.is_degraded

    @property
    def window(self) -> ClipRange | None:
        return self._window

    @property
    def fps(self) -> float:
        if self._metadata is None or self._metadata.fps <= 0.0:
            return FALLBACK_FPS
        return self._metadata.fps

    def apply_preferences(self, preferences: Preferences) -> None:
        self._policy.set_allow_degrade(preferences.adaptive_scrub)
        self._policy.set_coarse_interval_seconds(preferences.coarse_interval_seconds)
        self._render_fed = preferences.render_fed_playback
        self._cache.clear()
        if self._render_ring is not None:
            self._render_ring.set_proxy_width(preferences.proxy_width)
        self._proxy_width_changed.emit(preferences.proxy_width)

    def set_render_feed(self, ring: RenderFrameRing | None) -> None:
        self._render_ring = ring

    @Slot(bool)
    def set_render_filling(self, active: bool) -> None:
        self._render_filling = active

    @property
    def viewport_luma(self) -> bool:
        return self._viewport_luma

    @property
    def playback_rate(self) -> float:
        return self._playback_rate

    def set_playback_rate(self, rate: float) -> None:
        if rate <= 0.0 or rate == self._playback_rate:
            return
        self._playback_rate = rate
        self._anchor_playback(self._current_index)

    def set_viewport_luma(self, enabled: bool) -> None:
        if enabled == self._viewport_luma:
            return
        self._viewport_luma = enabled
        self._cache.clear()
        self._coalescer.new_generation()
        self._luma_changed.emit(enabled)
        if self._metadata is not None:
            self._request(self._current_index, RequestKind.EXACT)

    def open(self, path: str) -> None:
        self.pause()
        self._reset_source_state()
        self._open_requested.emit(path)

    def close(self) -> None:
        self.pause()
        self._reset_source_state()
        self._close_requested.emit()

    def set_window(self, window: ClipRange | None) -> None:
        self._window = window
        if self._metadata is None:
            return
        bounded = self._clamp(self._current_index)
        if bounded != self._current_index:
            self.seek(bounded)

    def seek(self, index: int) -> None:
        self._go_to(index, RequestKind.EXACT)

    def scrub(self, index: int) -> None:
        self._go_to(index, RequestKind.SCRUB)

    def step(self, delta: int) -> None:
        self.pause()
        self.seek(self._current_index + delta)

    def play(self) -> None:
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
        if not self._playing:
            return
        self._playing = False
        if self._tick_timer_id:
            self.killTimer(self._tick_timer_id)
            self._tick_timer_id = 0
        self.playing_changed.emit(False)

    def toggle_play(self) -> None:
        if self._playing:
            self.pause()
        else:
            self.play()

    def shutdown(self) -> None:
        self.pause()
        self._close_requested.emit()
        self._thread.quit()
        self._thread.wait()

    def timerEvent(self, event: object) -> None:
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
        target = (
            self._clamp(self._policy.snap(index))
            if kind is RequestKind.SCRUB
            else index
        )
        if self._display_cached(target, kind):
            return
        self._request(target, kind)

    def _display_cached(self, index: int, kind: RequestKind) -> bool:
        image = self._cache.get(index)
        if image is None:
            return False
        self._record(index, kind, FROM_CACHE)
        self._coalescer.served_without_decode(kind)
        self._current_index = index
        self.frame_changed.emit(index, image)
        return True

    def _anchor_playback(self, index: int) -> None:
        self._play_anchor_time = perf_counter()
        self._play_anchor_index = index

    def _bounds(self) -> ClipRange:
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
        if self._render_fed and self._viewport_luma:
            return self._render_ring
        return None

    def _display_from_ring(self, index: int, kind: RequestKind) -> bool:
        ring = self._feed_ring()
        if ring is None:
            return False
        image = ring.get(index)
        if image is None:
            return False
        self._record(index, kind, FROM_RING)
        self._coalescer.served_without_decode(kind)
        self._current_index = index
        self.frame_changed.emit(index, image)
        return True

    def _request(self, index: int, kind: RequestKind) -> None:
        if self._display_from_ring(index, kind):
            return
        self._record(index, kind, FROM_DECODE)
        self._issue(self._coalescer.request(index, kind))

    def _record(self, index: int, kind: RequestKind, source: str) -> None:
        if not self._trace.enabled:
            return
        ring = self._render_ring
        self._trace.record(
            AccessEvent(
                op=GET,
                index=index,
                playhead=self._current_index,
                kind=kind.value,
                source=source,
                frontier=None if ring is None else ring.frontier,
            )
        )

    def _issue(self, request: Request | None) -> None:
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
        if arrival.stale or arrival.request is None:
            self._issue(self._coalescer.drain())
            return
        if arrival.request.kind is not RequestKind.PLAYBACK:
            self._cache.put(index, image)
        if arrival.display:
            self._current_index = index
            self.frame_changed.emit(index, image)
        if arrival.request.kind is RequestKind.SCRUB:
            round_trip_ms = self._coalescer.round_trip_ms()
            self._metrics.publish("scrub_to_repaint", round_trip_ms)
            if self._policy.observe(round_trip_ms):
                self.scrub_degraded.emit()
        self._issue(self._coalescer.drain())

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        self._issue(self._coalescer.drain())
        self.pause()
        self.failed.emit(message)
