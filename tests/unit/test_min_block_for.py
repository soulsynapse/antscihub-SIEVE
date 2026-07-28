"""`min_block_for` is `grid_shape` read backwards, and must not disagree with it.

The Block spin box refuses sizes under this number, so the two ways it can be
wrong are the two ways a control can be: too low and the refusal does not
refuse — the stall it exists to prevent happens at a value the widget accepted
— or too high and it forbids block sizes the density surface would have binned
happily, which is a control lying about what the system can do.

Both are stated against `grid_shape` rather than against arithmetic written out
a second time here. A test that recomputed the ceiling division would pass a
`min_block_for` that disagreed with the kernel in exactly the same way.
"""

from __future__ import annotations

import pytest

from sieve.filters.block_signal import grid_shape, min_block_for

#: A 5.3K source, its half-scale, and two crop-shaped extents. Extreme aspect
#: ratios are in because the closed-form seed assumes a square grid and the
#: step-up from it is what has to survive them.
EXTENTS = [
    (2988, 5312),
    (1494, 2656),
    (600, 800),
    (120, 160),
    (17, 4001),
    (1, 1_000_000),
]

MAXIMA = [1, 64, 1024, 16_384, 1_000_000]


@pytest.mark.parametrize(("height", "width"), EXTENTS)
@pytest.mark.parametrize("max_blocks", MAXIMA)
def test_the_returned_block_fits_and_one_smaller_does_not(
    height: int, width: int, max_blocks: int
) -> None:
    """Exactly the boundary: it fits, and the next size down overflows.

    The second half is what makes this a *minimum*. Returning 64 whenever
    asked would satisfy the fit and would forbid most of the range.
    """
    block = min_block_for(height, width, max_blocks)
    ny, nx = grid_shape(height, width, block)
    assert ny * nx <= max_blocks

    if block > 1:
        py, px = grid_shape(height, width, block - 1)
        assert py * px > max_blocks


def test_a_bound_no_block_size_can_meet_returns_the_largest_useful_one() -> None:
    """`max_blocks = 1` on a rectangle: one block is the whole frame.

    The walk stops at `max(height, width)`, where the grid is 1x1 and cannot
    shrink further — without that stop the loop would climb forever on a bound
    of zero blocks, and a spin box floor of infinity is not a refusal, it is a
    hang at construction.
    """
    block = min_block_for(600, 800, 1)
    assert grid_shape(600, 800, block) == (1, 1)


def test_a_degenerate_extent_does_not_pretend_to_a_floor() -> None:
    """No source open yet, or a bound of nothing: the floor is 1.

    1 is the smallest block size that exists, so it refuses nothing — which is
    the honest answer when there is no extent to derive a refusal from.
    """
    assert min_block_for(0, 0, 16_384) == 1
    assert min_block_for(600, 800, 0) == 1
