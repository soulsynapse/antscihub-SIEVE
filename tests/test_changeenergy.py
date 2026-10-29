"""changeenergy: the squared difference, spread by the blur, in float32; row 0 has no other side."""
import numpy as np

from tools import changeenergy


def test_squared_difference_spread_by_the_blur_and_zero_at_row_zero():
    d = np.zeros((2, 16, 16), np.uint8)
    d[1, 8, 8] = 10                                        # one pixel changes by 10: energy 100, blurred
    frames = lambda r: d[r]  # noqa: E731
    out = changeenergy.run(frames, 1, {"sigma": 1.0})
    assert out.shape == (16, 16) and out.dtype == np.float32
    assert abs(out.sum() - 100.0) < 1e-3 and out[8, 8] == out.max() and 0.0 < out[8, 8] < 100.0
    assert out[8, 9] > 0.0 and out[0, 0] == 0.0           # the blur spreads it, not that far
    assert not changeenergy.run(frames, 0, {"sigma": 1.0}).any()
