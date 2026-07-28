"""The render's recent source frames, kept as display proxies for the player.

Render-fed playback's buffer. While a window render fills, the preview thread
decodes every frame of the window — the very frames the player would decode
again to show them, and the two readers contend on the bandwidth that is
actually scarce (`docs/findings/2026.07.27-decode-is-a-bandwidth-wall-shared-
by-two-consumers.md`). The frames are discarded, not unavailable: `execute`
drops its decoded source after the graph consumes it. This ring is where they
go instead — written once per frame on the render thread, read by the player
on the GUI thread, so the pane can show what the render already paid for and
the second decode never happens.

Deliberately not `ProxyFrameCache` at the call site, though one sits inside:
that cache is the *scrub* cache, GUI-thread-owned, warmed by the user's own
returns, and `gui/proxy_cache.py` says why playback must not evict it. This
is a render-owned buffer with a different lifetime (cleared when the source
closes, frontier reset when a window render starts) and a lock, because it is
the one image store two threads touch. The LRU inside is the right eviction
here too: the player loops over the rendered prefix while the window fills,
and touching a frame on the way past is what keeps the loop's span resident.

The proxies are luma. The pipeline decodes gray for every graph on today's
shelf, and the pane can only take these frames while it shows gray itself —
which is the dependency the item stated: the gray viewport is what makes the
render's format and the player's the same format. A chroma frame offered to
`put` is refused rather than converted; the day a graph needs chroma, the
honest behaviour is the old one (the player decodes for itself), not a
conversion pass nobody measured.

The bound is `RENDER_RING_SHARE` in `gui/concurrency.py` — declared there so
the ledger's sum stays the whole session. It is a 256 MB floor with a 1%
fraction: capacity, not eviction order, is what its hit rate turned out to be
made of (`docs/findings/2026.07.28-capacity-beats-policy-in-the-render-ring.md`),
so a bigger machine gets a bigger ring rather than a cleverer one.

Every accepted `put` is offered to `bench/retention_trace.py`, which is off
unless a session declares a path — the render's production sequence is half of
what that experiment replays, and it exists nowhere else.

The frontier is "the last frame the render has produced", reset when a window
render starts. It is *not* the settled frontier (`DetectorResult.settled` is
"will not change", this is "exists"), and the player folds playback at this
one only while a render is filling — `timeline_model.feed_bounds` is that
arithmetic.
"""

from __future__ import annotations

from threading import Lock

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from sieve.bench.retention_trace import (
    PUT,
    TRACE,
    UNKNOWN_PLAYHEAD,
    AccessEvent,
    TraceRecorder,
)
from sieve.core.types import ChannelSpec, Frame
from sieve.gui.concurrency import RENDER_RING_SHARE, resolved_bytes
from sieve.gui.decode_worker import PROXY_WIDTH
from sieve.gui.proxy_cache import ProxyFrameCache


class RenderFrameRing:
    """Bounded, lock-guarded ring of the render's source frames as gray proxies."""

    def __init__(
        self, capacity_bytes: int | None = None, *, trace: TraceRecorder | None = None
    ) -> None:
        self._lock = Lock()
        # Off unless a session was started with `SIEVE_RETENTION_TRACE` set.
        # Injectable so a test hears only its own writes, for the reason
        # `bench/metrics.py` gives about the process-wide bus.
        self._trace = TRACE if trace is None else trace
        self._frames = ProxyFrameCache(
            capacity_bytes=resolved_bytes(RENDER_RING_SHARE)
            if capacity_bytes is None
            else capacity_bytes
        )
        # The decode thread's own starting width, for the same reason it is
        # that module's: these frames stand in for that thread's output. The
        # preference overrides both through `VideoPlayer.apply_preferences`.
        self._proxy_width = PROXY_WIDTH
        self._frontier: int | None = None

    @property
    def frontier(self) -> int | None:
        """Index of the newest frame the filling render produced, or None."""
        with self._lock:
            return self._frontier

    def set_proxy_width(self, width: int) -> None:
        """Adopt the display width. Retained frames are the old width — dropped."""
        with self._lock:
            if width == self._proxy_width:
                return
            self._proxy_width = max(width, 1)
            self._frames.clear()

    def begin(self) -> None:
        """A window render is starting: its frontier starts from nothing.

        Frames are kept — the source has not changed, so a proxy at index `i`
        is still the frame at index `i` whatever the chain now computes. Only
        the frontier resets, because it is a claim about *this* render.
        """
        with self._lock:
            self._frontier = None

    def put(self, frame: Frame) -> None:
        """Keep `frame` as a proxy and advance the frontier. Render thread.

        A chroma frame is refused whole — no proxy, no frontier move — so the
        player never folds toward frames it could not take (see module
        docstring for why conversion is not the answer).
        """
        if frame.channels is not ChannelSpec.GRAY or frame.data.dtype != np.uint8:
            return
        data = np.ascontiguousarray(frame.data)
        height, width = data.shape[:2]
        image = QImage(data.tobytes(), width, height, width, QImage.Format.Format_Grayscale8)
        with self._lock:
            if 0 < self._proxy_width < width:
                image = image.scaledToWidth(
                    self._proxy_width, Qt.TransformationMode.SmoothTransformation
                )
            else:
                # QImage does not own the buffer it was built over; the copy
                # is what lets the numpy array die. `scaledToWidth` above
                # allocates its own pixels, so only this branch needs it.
                image = image.copy()
            self._frames.put(frame.index, image)
            self._frontier = frame.index
        if self._trace.enabled:
            self._trace.record(
                AccessEvent(
                    op=PUT,
                    index=frame.index,
                    playhead=UNKNOWN_PLAYHEAD,
                    kind="",
                    source="",
                    frontier=frame.index,
                )
            )

    def get(self, index: int) -> QImage | None:
        """The proxy at `index`, or None. GUI thread; a hit refreshes its LRU slot."""
        with self._lock:
            return self._frames.get(index)

    def clear(self) -> None:
        """Drop everything, frontier included. Called when the source changes."""
        with self._lock:
            self._frames.clear()
            self._frontier = None
