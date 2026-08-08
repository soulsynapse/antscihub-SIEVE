"""The two proportions `test_timeline.py` cannot hold, and the numbers they carry.

That file lays a 1000-px strip over a 1000-frame source so every frame owns
exactly one column, which is what makes its arithmetic readable and also what
makes `width` and `width - 1` agree everywhere a case looks, and every band it
paints wider than the floor. Both decisions below are argued in `geometry.py`
and are invisible at that proportion: they need a source far longer than the
band, and a band far wider than the source is long.

`geometry.py` is Qt-free, so nothing here asks for a `QApplication`.
"""

from __future__ import annotations

import pytest

#: An hour at 30 fps across a thousand pixels: one frame is a hundredth of a
#: pixel, which is the source length a tuning session actually opens.
LONG_SOURCE_FRAMES = 108_000

#: Ten frames across the same thousand pixels: one frame owns a hundred columns.
SHORT_SOURCE_FRAMES = 10

BAND_WIDTH = 1000.0


def test_a_window_too_narrow_to_see_is_painted_at_the_floor() -> None:
    """A one-frame window in a long source, which is the width the floor is for.

    Widened rightward, so the left edge is still the frame's own column: a band
    rounded up symmetrically would report a window starting before the frame the
    user marked.
    """
    from sieve.gui.timeline.geometry import MIN_BAND_PIXELS, Geometry

    band = Geometry(frame_count=LONG_SOURCE_FRAMES, width=BAND_WIDTH)
    left, right = band.span(40_000, 40_001)

    assert left == pytest.approx(band.x_of_frame(40_000))
    assert right - left == pytest.approx(MIN_BAND_PIXELS)


def test_the_last_column_starts_where_it_is_painted_and_not_a_pixel_early() -> None:
    """`frame_at` inverts `x_of_frame`, over the full width and not `width - 1`.

    The off-by-one denominator drags every boundary left by that frame's share
    of a pixel, most at the last one: half a pixel short of 900 is still inside
    the ninth column, and a mapping divided by 999 calls it the tenth.
    """
    from sieve.gui.timeline.geometry import Geometry

    band = Geometry(frame_count=SHORT_SOURCE_FRAMES, width=BAND_WIDTH)
    last = SHORT_SOURCE_FRAMES - 1
    boundary = band.x_of_frame(last)

    assert boundary == pytest.approx(900.0)
    assert band.frame_at(boundary) == last
    assert band.frame_at(boundary - 0.5) == last - 1
