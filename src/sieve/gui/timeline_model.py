


































from __future__ import annotations

from dataclasses import dataclass

from sieve.core.pipeline_model import ClipRange





DEFAULT_WINDOW_SECONDS = 10.0





MIN_BAND_PIXELS = 2.0


def default_window(frame_count: int, fps: float) -> ClipRange | None:







    if frame_count <= 0:
        return None
    if fps <= 0.0:
        return ClipRange(start=0, end=frame_count)
    length = min(max(round(DEFAULT_WINDOW_SECONDS * fps), 1), frame_count)
    return ClipRange(start=0, end=length)


def effective_window(clip: ClipRange | None, frame_count: int, fps: float) -> ClipRange | None:









    if clip is None:
        return default_window(frame_count, fps)
    return clip


def moved_to(window: ClipRange, origin: int, frame_count: int) -> ClipRange:








    length = min(window.frame_count, frame_count)
    start = min(max(origin, 0), frame_count - length)
    return ClipRange(start=start, end=start + length)


def containing(window: ClipRange, frame: int, frame_count: int) -> ClipRange:







    if window.start <= frame < window.end:
        return window
    origin = frame if frame < window.start else frame - window.frame_count + 1
    return moved_to(window, origin, frame_count)


def ended_at(window: ClipRange | None, frame: int, frame_count: int) -> ClipRange:








    end = min(max(frame, 0), frame_count - 1) + 1
    start = 0
    if window is not None and window.start < end:
        start = window.start
    return ClipRange(start=start, end=end)


def started_at(window: ClipRange, frame: int, frame_count: int, floor: int) -> ClipRange:











    limit = min(max(floor, 1), frame_count)
    end = min(max(window.end, limit), frame_count)
    return ClipRange(start=min(max(frame, 0), end - limit), end=end)


def ended_at_handle(window: ClipRange, frame: int, frame_count: int, floor: int) -> ClipRange:








    limit = min(max(floor, 1), frame_count)
    start = min(max(window.start, 0), frame_count - limit)
    return ClipRange(start=start, end=min(max(frame + 1, start + limit), frame_count))


def fitted(window: ClipRange | None, frame_count: int) -> ClipRange | None:








    if window is None or frame_count <= 0 or window.start >= frame_count:
        return None
    return ClipRange(start=window.start, end=min(window.end, frame_count))


def feed_bounds(window: ClipRange, frontier: int | None) -> ClipRange:














    if frontier is None or frontier < window.start:
        return window
    return ClipRange(start=window.start, end=min(window.end, frontier + 1))


@dataclass(frozen=True, slots=True)
class PlaybackStep:








    index: int
    rewound: bool


def playback_step(target: int, current: int, window: ClipRange) -> PlaybackStep:










    if target < window.start:
        return PlaybackStep(index=window.start, rewound=True)
    if target < window.end:
        return PlaybackStep(index=target, rewound=False)
    if current != window.end - 1:
        return PlaybackStep(index=window.end - 1, rewound=False)
    return PlaybackStep(index=window.start, rewound=True)


@dataclass(frozen=True, slots=True)
class Geometry:








    frame_count: int
    width: float

    @property
    def is_empty(self) -> bool:

        return self.frame_count <= 0 or self.width <= 0.0

    def x_of_frame(self, frame: int) -> float:





        if self.is_empty:
            return 0.0
        bounded = min(max(frame, 0), self.frame_count)
        return bounded / self.frame_count * self.width

    def centre_of_frame(self, frame: int) -> float:






        if self.is_empty:
            return 0.0
        bounded = min(max(frame, 0), self.frame_count - 1)
        return (bounded + 0.5) / self.frame_count * self.width

    def span(self, start: int, end: int) -> tuple[float, float]:






        left = self.x_of_frame(start)
        right = max(self.x_of_frame(end), left + MIN_BAND_PIXELS)
        return left, right

    def frame_at(self, x: float) -> int:







        if self.is_empty:
            return 0
        index = int(x / self.width * self.frame_count)
        return min(max(index, 0), self.frame_count - 1)
