"""blobs: the nonzero regions of a mask or gray plane as a table, with area bounds, moments, the diff
input's intensity columns, and splitting; the display falls back to what it read."""
import numpy as np

from sieve_player.window import imageable
from tools import blobs

m = np.zeros((10, 12), np.uint8)
m[1:4, 1:5] = 255                                          # 12 px
m[6:9, 7:10] = 255                                         # 9 px
m[0, 11] = 255                                             # 1 px of speckle


def fed(mask, diff=None):
    return lambda r, name="in": mask if name == "in" else diff


def test_regions_as_records_with_area_bounds_from_mask_or_gray():
    out = blobs.run(fed(m), 0, {**blobs.DEFAULTS, "min_area": 2})
    assert out.dtype == blobs.DTYPE and out.ndim == 1 and len(out) == 2 and sorted(out["area"]) == [9, 12]
    big = out[out["area"] == 12][0]
    assert (big["x"], big["y"], big["w"], big["h"]) == (1, 1, 4, 3) and (big["cx"], big["cy"]) == (2.5, 2.0)
    assert big["angle"] == 0 and big["major"] > big["minor"] > 0 and np.isnan(big["mean"]) and big["core"] == -1
    assert big["contour"].shape == (4, 2) and big["contour"].min(axis=0).tolist() == [1, 1]   # the box's corners
    assert len(blobs.run(fed(m), 0, {**blobs.DEFAULTS, "min_area": 0})) == 3
    assert len(blobs.run(fed(m), 0, {**blobs.DEFAULTS, "min_area": 2, "max_area": 10})) == 1
    gray = (m // 5).astype(np.uint8)                           # a faint plane: nonzero is foreground
    assert len(blobs.run(fed(gray), 0, {**blobs.DEFAULTS, "min_area": 2})) == 2
    empty = blobs.run(fed(np.zeros((4, 4), np.uint8)), 0, blobs.DEFAULTS)
    assert len(empty) == 0 and empty.dtype == blobs.DTYPE
    assert not imageable(out) and imageable(m) and imageable(np.zeros((4, 4, 3), np.uint8))


def test_a_long_region_reads_its_angle_and_the_diff_input_its_core():
    mask = np.zeros((20, 20), np.uint8)
    for i in range(10):
        mask[5 + i, 4 + i] = mask[6 + i, 4 + i] = 255          # a diagonal bar, 45 degrees
    diff = np.where(mask > 0, 10, 0).astype(np.uint8)
    diff[8:12, 7:11] = 90                                      # a bright core in the middle
    b = blobs.run(fed(mask, diff), 0, {**blobs.DEFAULTS, "min_area": 1, "core_threshold": 50})[0]
    assert abs(abs(b["angle"]) - 45) < 2 and b["major"] > 2 * b["minor"]
    assert b["peak"] == 90 and 10 < b["mean"] < 90 and b["core"] == np.count_nonzero(mask & (diff >= 50))


def test_a_region_over_max_area_is_split_at_a_higher_cut_or_dropped():
    diff = np.zeros((10, 20), np.uint8)
    diff[2:8, 2:8], diff[2:8, 11:17] = 60, 60                  # two bright squares, 36 px each
    diff[4:6, 8:11] = 20                                       # joined by a dim bridge
    mask = (diff > 0).astype(np.uint8) * 255
    params = {"min_area": 10, "max_area": 40, "core_threshold": 0, "split": True}
    out = blobs.run(fed(mask, diff), 0, params)
    assert len(out) == 2 and sorted(out["area"]) == [36, 36] and sorted(out["x"]) == [2, 11]
    assert len(blobs.run(fed(mask, diff), 0, {**params, "split": False})) == 0
    assert len(blobs.run(fed(mask), 0, params)) == 0                         # no diff: nothing to cut at
    solid = np.full((10, 10), 60, np.uint8)
    assert len(blobs.run(fed(solid, solid), 0, params)) == 0                 # no cut splits it
