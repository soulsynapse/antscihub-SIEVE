"""Playback and seek control on the GUI thread.

Two things make this more than a timer.

**Request coalescing.** At most one decode request is in flight at a time and
at most one is pending. A scrub that outruns the decoder therefore discards
the frames nobody would have seen instead of queueing them, so releasing the
slider shows the frame under the cursor rather than replaying the drag. This
is what keeps perceived scrub latency near the cost of one decode no matter
how fast the user moves.

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

from sieve.core.types import VideoMetadata
from sieve.gui.decode_worker import DecodeWorker

#: How often playback re-evaluates which frame the clock is on. Finer than any
#: source frame rate we expect, so the limit on smoothness is decode, not this.
TICK_INTERVAL_MS = 8

#: Frame rate assumed when the container reports a nonsensical one.
FALLBACK_FPS = 30.0


class VideoPlayer(QObject):
    """Owns the decode thread and the transport state for one video."""

    opened = Signal(VideoMetadata)
    failed = Signal(str)
    frame_changed = Signal(int, QImage)
    playing_changed = Signal(bool)

    _open_requested = Signal(str)
    _frame_requested = Signal(int)
    _close_requested = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._metadata: VideoMetadata | None = None
        self._current_index = 0
        self._in_flight: int | None = None
        self._pending: int | None = None

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
    def fps(self) -> float:
        """Effective frame rate, substituting a fallback for unusable metadata."""
        if self._metadata is None or self._metadata.fps <= 0.0:
            return FALLBACK_FPS
        return self._metadata.fps

    # ---- transport -------------------------------------------------------

    def open(self, path: str) -> None:
        """Load a video. `opened` or `failed` follows."""
        self.pause()
        self._metadata = None
        self._current_index = 0
        self._in_flight = None
        self._pending = None
        self._open_requested.emit(path)

    def close(self) -> None:
        """Unload the current video."""
        self.pause()
        self._metadata = None
        self._current_index = 0
        self._in_flight = None
        self._pending = None
        self._close_requested.emit()

    def seek(self, index: int) -> None:
        """Jump to `index`, re-anchoring playback there if it is running."""
        if self._metadata is None:
            return
        index = self._clamp(index)
        self._anchor_playback(index)
        self._request(index)

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
            self._request(self._metadata.frame_count - 1)
            return
        if target != self._current_index or self._in_flight is not None:
            self._request(target)

    def _anchor_playback(self, index: int) -> None:
        self._play_anchor_time = perf_counter()
        self._play_anchor_index = index

    def _clamp(self, index: int) -> int:
        if self._metadata is None:
            return 0
        return max(0, min(index, self._metadata.frame_count - 1))

    def _request(self, index: int) -> None:
        """Ask the decode thread for a frame, coalescing against any in flight."""
        if self._in_flight is not None:
            self._pending = index
            return
        self._in_flight = index
        self._frame_requested.emit(index)

    def _drain(self) -> None:
        self._in_flight = None
        if self._pending is not None:
            next_index, self._pending = self._pending, None
            self._request(next_index)

    @Slot(VideoMetadata)
    def _on_opened(self, metadata: VideoMetadata) -> None:
        self._metadata = metadata
        self._current_index = 0
        self.opened.emit(metadata)
        self._request(0)

    @Slot(int, QImage)
    def _on_frame_ready(self, index: int, image: QImage) -> None:
        self._current_index = index
        self.frame_changed.emit(index, image)
        self._drain()

    @Slot(str)
    def _on_failed(self, message: str) -> None:
        # Clearing in-flight here matters: a decode error that left the slot
        # occupied would wedge every later request behind it.
        self._drain()
        self.pause()
        self.failed.emit(message)
