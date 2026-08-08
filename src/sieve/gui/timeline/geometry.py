"""Where a frame lands on the strip, and which frame a pixel names.

Qt-free by the same argument as `transport/pacing.py`: the mapping can be off by
a column at the first or last frame — exactly where a user marking the start or
the end of a video is looking, and nowhere a mid-band test would catch.

The band spans the whole asset with no handle to make room for, so the mapping
is proportional — `frame / frame_count * width`. A frame owns the *column*
starting at `x_of_frame`, which is why a span's right edge is `x_of_frame(end)`
and not `x_of_frame(end - 1)`: the window runs up to the start of the frame
after its last, so a one-frame window is one column wide instead of zero.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Narrowest a painted span may be. A window of one frame in a two-hour source
#: is a fraction of a pixel, and a band nobody can see reads as no band at all —
#: which is the same failure as painting the wrong span, arriving through the
#: width instead of through the position.
MIN_BAND_PIXELS = 2.0


@dataclass(frozen=True, slots=True)
class Geometry:
    """The frame↔column mapping for a band `width` pixels wide over `frame_count`.

    Constructed per paint and per click rather than held, because both of its
    fields change under the user: a resized window changes the width and an
    opened video changes the count, and a cached mapping is one that paints the
    previous video's proportions until something invalidates it.
    """

    frame_count: int
    width: float

    @property
    def is_empty(self) -> bool:
        """Whether there is anything to map. Nothing is drawn or hit-tested if so."""
        return self.frame_count <= 0 or self.width <= 0.0

    def x_of_frame(self, frame: int) -> float:
        """Left edge of the column `frame` occupies.

        Accepts `frame_count` itself, which is not a frame: it is where the
        asset ends, and a half-open span's right edge lands on it.
        """
        if self.is_empty:
            return 0.0
        bounded = min(max(frame, 0), self.frame_count)
        return bounded / self.frame_count * self.width

    def centre_of_frame(self, frame: int) -> float:
        """Middle of the column `frame` occupies — where the playhead is drawn.

        The playhead is a claim about one frame, and one frame is a column, not
        a boundary. Drawn at the left edge it sits between two frames and reads
        as pointing at the earlier one at the end of a scrub.
        """
        if self.is_empty:
            return 0.0
        bounded = min(max(frame, 0), self.frame_count - 1)
        return (bounded + 0.5) / self.frame_count * self.width

    def span(self, start: int, end: int) -> tuple[float, float]:
        """Left and right edges of the half-open span `[start, end)`, in pixels.

        Never narrower than `MIN_BAND_PIXELS`, and widened rightward from the
        left edge so the span's *position* stays true when its width is being
        rounded up.
        """
        left = self.x_of_frame(start)
        right = max(self.x_of_frame(end), left + MIN_BAND_PIXELS)
        return left, right

    def frame_at(self, x: float) -> int:
        """The frame whose column contains `x`, clamped to the asset.

        The inverse of `x_of_frame` over the full width, and neither of the two
        off-by-one versions it is mistaken for. Dividing by `width - 1` names
        the last frame a pixel early — over ten frames in a 1000-pixel band,
        from x = 899.1 rather than from 900 — and goes on naming it from there
        to the right edge. Multiplying by `frame_count - 1` is the one that
        never names the last frame for a click inside the band at all: its
        boundary lands on the band's right edge.
        """
        if self.is_empty:
            return 0
        index = int(x / self.width * self.frame_count)
        return min(max(index, 0), self.frame_count - 1)
