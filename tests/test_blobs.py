"""blobs: the nonzero regions of a mask or gray plane as a table, with area bounds; the display falls back to what it read."""
import numpy as np

from sieve_player.window import imageable
from tools import blobs


def test_regions_as_records_with_area_bounds_from_mask_or_gray():
    m = np.zeros((10, 12), np.uint8)
    m[1:4, 1:5] = 255                                          # 12 px
    m[6:9, 7:10] = 255                                         # 9 px
    m[0, 11] = 255                                             # 1 px of speckle
    out = blobs.run(lambda r: m, 0, {"min_area": 2, "max_area": 0})
    assert out.dtype == blobs.DTYPE and out.ndim == 1 and len(out) == 2 and sorted(out["area"]) == [9, 12]
    big = out[out["area"] == 12][0]
    assert (big["x"], big["y"], big["w"], big["h"]) == (1, 1, 4, 3) and (big["cx"], big["cy"]) == (2.5, 2.0)
    assert len(blobs.run(lambda r: m, 0, {"min_area": 0, "max_area": 0})) == 3
    assert len(blobs.run(lambda r: m, 0, {"min_area": 2, "max_area": 10})) == 1
    gray = (m // 5).astype(np.uint8)                           # a faint plane: nonzero is foreground
    assert len(blobs.run(lambda r: gray, 0, {"min_area": 2, "max_area": 0})) == 2
    empty = blobs.run(lambda r: np.zeros((4, 4), np.uint8), 0, blobs.DEFAULTS)
    assert len(empty) == 0 and empty.dtype == blobs.DTYPE
    assert not imageable(out) and imageable(m) and imageable(np.zeros((4, 4, 3), np.uint8))
