








from __future__ import annotations

from hypothesis import assume, given
from hypothesis import strategies as st

from sieve.core.types import ROI



COORDINATE = st.integers(min_value=0, max_value=20_000)
EXTENT = st.integers(min_value=1, max_value=20_000)
CORNER = st.integers(min_value=0, max_value=20_000)

ROIS = st.builds(ROI, x=COORDINATE, y=COORDINATE, width=EXTENT, height=EXTENT)


@given(roi=ROIS, width=EXTENT, height=EXTENT)
def test_clamped_to_lands_inside_the_frame_with_positive_extent(
    roi: ROI, width: int, height: int
) -> None:








    clamped = roi.clamped_to(width, height)

    assert clamped.width >= 1
    assert clamped.height >= 1
    assert clamped.x >= 0
    assert clamped.y >= 0
    assert clamped.right <= width
    assert clamped.bottom <= height


@given(roi=ROIS, width=EXTENT, height=EXTENT)
def test_clamped_to_is_a_projection(roi: ROI, width: int, height: int) -> None:





    clamped = roi.clamped_to(width, height)

    assert clamped.clamped_to(width, height) == clamped


@given(roi=ROIS, width=EXTENT, height=EXTENT)
def test_clamped_to_never_grows_the_region(roi: ROI, width: int, height: int) -> None:
    clamped = roi.clamped_to(width, height)

    assert clamped.width <= roi.width
    assert clamped.height <= roi.height


@given(x0=CORNER, y0=CORNER, x1=CORNER, y1=CORNER)
def test_from_corners_does_not_care_which_corner_came_first(
    x0: int, y0: int, x1: int, y1: int
) -> None:






    assume(x0 != x1 and y0 != y1)
    expected = ROI.from_corners(x0, y0, x1, y1)

    assert ROI.from_corners(x1, y0, x0, y1) == expected
    assert ROI.from_corners(x0, y1, x1, y0) == expected
    assert ROI.from_corners(x1, y1, x0, y0) == expected


@given(x0=CORNER, y0=CORNER, x1=CORNER, y1=CORNER)
def test_from_corners_covers_both_corners_exactly(x0: int, y0: int, x1: int, y1: int) -> None:

    assume(x0 != x1 and y0 != y1)
    roi = ROI.from_corners(x0, y0, x1, y1)

    assert roi.x == min(x0, x1)
    assert roi.y == min(y0, y1)
    assert roi.right == max(x0, x1)
    assert roi.bottom == max(y0, y1)
