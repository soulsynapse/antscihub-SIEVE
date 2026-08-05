"""When to stop decoding every scrub target, and what to decode instead.

The scrub budget cannot be met by decoding faster. Measured on the reference
source, a random seek is ~68 ms of which ~47 ms is `set(CAP_PROP_POS_FRAMES)`
before a single pixel is converted; hardware acceleration does not engage in
our OpenCV build, and skipping the colour conversion saves ~6 ms. There is no
tuning left. On a machine slower than the reference there is less than none.

So the budget is held by asking for less. Above a sustained latency threshold
the player stops treating the drag position as a frame index and starts
treating it as a *region*: targets snap to a coarse time grid, and because the
grid is small and stable, the frames land in the cache and recur. A drag over
warmed grid points costs nothing at all — the expensive thing is the seek, and
a cache hit does not seek. Exactness is restored the moment the drag ends.

Two properties keep this honest rather than merely cheap:

**It degrades on evidence, not on a guess about the hardware.** The trigger is
the median of a short window of *observed* scrub latencies, so a machine that
is keeping up is never degraded and one hiccup never flips it.

**It is sticky for the session and announced once.** Decode speed is a
property of the machine and the footage, not of the moment, so oscillating
between modes would be noise. The user is told once and can turn it off.
"""

from __future__ import annotations

from collections import deque
from enum import StrEnum
from statistics import median

#: Scrub latencies considered when deciding to degrade. Small enough to react
#: within a single drag, large enough that one slow seek is outvoted.
SAMPLE_WINDOW = 5

#: Default spacing of the coarse grid. One second is coarse enough to collapse
#: a full-timeline drag to a few dozen distinct targets and fine enough that
#: the frame on screen is never more than half a second from the cursor.
DEFAULT_COARSE_INTERVAL_SECONDS = 1.0

#: Frame rate assumed when converting the interval to a stride with no usable
#: metadata. Only affects grid spacing, so being wrong is cosmetic.
FALLBACK_FPS = 30.0


class ScrubMode(StrEnum):
    """Whether a drag position means a frame or a neighbourhood."""

    EXACT = "exact"
    COARSE = "coarse"


class ScrubPolicy:
    """Decides the mode, and snaps drag targets to the grid while degraded.

    Deliberately free of Qt and of any reference to the player: it is a
    decision made from latency samples, which makes it testable by feeding it
    numbers rather than by driving a GUI at a real video.
    """

    def __init__(
        self,
        budget_ms: float,
        *,
        coarse_interval_seconds: float = DEFAULT_COARSE_INTERVAL_SECONDS,
        allow_degrade: bool = True,
    ) -> None:
        self._budget_ms = budget_ms
        self._coarse_interval_seconds = coarse_interval_seconds
        self._allow_degrade = allow_degrade
        self._fps = FALLBACK_FPS
        self._samples: deque[float] = deque(maxlen=SAMPLE_WINDOW)
        self._mode = ScrubMode.EXACT

    # ---- state -----------------------------------------------------------

    @property
    def mode(self) -> ScrubMode:
        """The mode in force right now."""
        return self._mode

    @property
    def is_degraded(self) -> bool:
        """Whether drag targets are currently being snapped."""
        return self._mode is ScrubMode.COARSE

    @property
    def stride(self) -> int:
        """Grid spacing in frames. At least 1, so snapping is always defined."""
        return max(1, round(self._fps * self._coarse_interval_seconds))

    # ---- configuration ---------------------------------------------------

    def set_fps(self, fps: float) -> None:
        """Set the source frame rate the grid is derived from."""
        self._fps = fps if fps > 0.0 else FALLBACK_FPS

    def set_coarse_interval_seconds(self, seconds: float) -> None:
        """Set the grid spacing in seconds of source time."""
        self._coarse_interval_seconds = max(seconds, 0.0)

    def set_allow_degrade(self, allowed: bool) -> None:
        """Permit or forbid degradation.

        Forbidding it returns to exact scrubbing immediately rather than at the
        next drag: the user turning this off in Preferences is asking to see
        the effect now, not eventually.
        """
        self._allow_degrade = allowed
        if not allowed:
            self._mode = ScrubMode.EXACT
            self._samples.clear()

    def reset(self) -> None:
        """Forget the evidence. Called when the source changes."""
        self._samples.clear()
        self._mode = ScrubMode.EXACT

    # ---- decisions -------------------------------------------------------

    def snap(self, index: int) -> int:
        """The frame to actually decode for a drag that landed on `index`."""
        if self._mode is ScrubMode.EXACT:
            return index
        stride = self.stride
        return max(0, round(index / stride) * stride)

    def observe(self, latency_ms: float) -> bool:
        """Record one scrub decode's round trip.

        Returns True exactly once, on the transition into coarse mode, so the
        caller can announce it without tracking the edge itself.
        """
        if self._mode is ScrubMode.COARSE or not self._allow_degrade:
            return False

        self._samples.append(latency_ms)
        if len(self._samples) < SAMPLE_WINDOW:
            return False
        if median(self._samples) <= self._budget_ms:
            return False

        self._mode = ScrubMode.COARSE
        return True
