

























from __future__ import annotations

from collections import deque
from enum import StrEnum
from statistics import median



SAMPLE_WINDOW = 5




DEFAULT_COARSE_INTERVAL_SECONDS = 1.0



FALLBACK_FPS = 30.0


class ScrubMode(StrEnum):


    EXACT = "exact"
    COARSE = "coarse"


class ScrubPolicy:







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



    @property
    def mode(self) -> ScrubMode:

        return self._mode

    @property
    def is_degraded(self) -> bool:

        return self._mode is ScrubMode.COARSE

    @property
    def stride(self) -> int:

        return max(1, round(self._fps * self._coarse_interval_seconds))



    def set_fps(self, fps: float) -> None:

        self._fps = fps if fps > 0.0 else FALLBACK_FPS

    def set_coarse_interval_seconds(self, seconds: float) -> None:

        self._coarse_interval_seconds = max(seconds, 0.0)

    def set_allow_degrade(self, allowed: bool) -> None:






        self._allow_degrade = allowed
        if not allowed:
            self._mode = ScrubMode.EXACT
            self._samples.clear()

    def reset(self) -> None:

        self._samples.clear()
        self._mode = ScrubMode.EXACT



    def snap(self, index: int) -> int:

        if self._mode is ScrubMode.EXACT:
            return index
        stride = self.stride
        return max(0, round(index / stride) * stride)

    def observe(self, latency_ms: float) -> bool:





        if self._mode is ScrubMode.COARSE or not self._allow_degrade:
            return False

        self._samples.append(latency_ms)
        if len(self._samples) < SAMPLE_WINDOW:
            return False
        if median(self._samples) <= self._budget_ms:
            return False

        self._mode = ScrubMode.COARSE
        return True
