"""motion: the row's |difference| from the row before, in the upstream's shape; row 0 has no other side."""
import numpy as np

from tools import motion


def test_difference_from_the_previous_row_and_zero_at_row_zero():
    d = np.zeros((3, 8, 8), np.uint8)
    d[2, 2:4, 2:4] = 200                                   # row 2 differs from row 1 in one 2x2 patch
    frames = lambda r: d[r]  # noqa: E731
    out = motion.run(frames, 2, {})
    assert out.shape == (8, 8) and out.dtype == np.uint8 and out.sum() == 800 and out[2, 2] == 200
    assert not motion.run(frames, 1, {}).any()
    assert motion.run(frames, 0, {}).tolist() == np.zeros((8, 8)).tolist()
