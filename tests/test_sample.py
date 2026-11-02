"""sample: a plane's mean, max or count inside each record's own contour as a named column; a plane of
another shape is read in its coordinates, the same at twice and at half; a painted region samples
as membership."""
import numpy as np
import pytest

from tests.test_blobs import fed
from tools import blobs, filter, paint, sample

M = np.zeros((8, 8), np.uint8)
M[1:7, 1:3] = 255
M[5:7, 1:6] = 255                        # an L, 18 px
M[1:3, 5:7] = 255                        # a square away from it, 4 px
FOUND = blobs.run(fed(M), 0, {**blobs.DEFAULTS, "min_area": 2})
ELL, SQUARE = list(FOUND["area"]).index(18), list(FOUND["area"]).index(4)


def patch(shape, lo, hi, value=200):
    p = np.zeros(shape, np.uint8)
    p[lo[0]:hi[0], lo[1]:hi[1]] = value
    return p


def test_a_statistic_inside_the_records_own_contour_not_its_box():
    plane = patch(M.shape, (1, 1), (7, 6), 200)
    plane[1:5, 3:6] = 50                       # inside the L's box, outside the L
    plane[1:3, 5:7] = 0                        # nothing under the square
    for method, ell, square in (("mean", 200.0, 0.0), ("max", 200.0, 0.0), ("count", 18, 0)):
        out = sample.run(fed(FOUND, plane), 0, {"column": "under", "method": method})
        assert out.dtype.names[-1] == "under" and blobs.plane(out) == M.shape
        assert out["under"][ELL] == ell and out["under"][SQUARE] == square
    assert filter.keep(out, "under", "1", "")["area"].tolist() == [18]
    with pytest.raises(ValueError):
        sample.sample(FOUND, plane, "area")
    with pytest.raises(ValueError):
        sample.sample(FOUND, plane, "under", "median")


def test_a_plane_of_another_shape_is_read_in_its_coordinates():
    half, same, twice = np.zeros((4, 4), np.uint8), patch(M.shape, (1, 3), (3, 7)), np.zeros((16, 16), np.uint8)
    half[0:1, 2:4] = 200                       # the square at half: rows 1-2 and cols 5-6 at full
    twice[2:6, 10:14] = 200
    for method in ("mean", "max"):
        reads = [sample.sample(FOUND, p, "s", method)["s"].tolist() for p in (half, same, twice)]
        assert reads[0] == reads[1] == reads[2] and reads[0][SQUARE] == 200.0 and reads[0][ELL] == 0.0
    counts = [sample.sample(FOUND, p, "s", "count")["s"][SQUARE] for p in (half, same, twice)]
    assert counts == [1, 4, 16]                # count is the plane's own pixels


def test_a_painted_region_samples_as_membership():
    wide = blobs.run(fed(patch(M.shape, (0, 0), (8, 6), 255)), 0, {**blobs.DEFAULTS, "min_area": 2})
    members = sample.sample(FOUND, paint.paint(wide), "nest", "mean")
    assert members["nest"][ELL] == 255.0 and members["nest"][SQUARE] == 127.5
    assert sample.sample(FOUND, paint.paint(wide), "nest", "count")["nest"].tolist()[SQUARE] == 2
    narrow = blobs.run(fed(patch(M.shape, (0, 0), (8, 3), 255)), 0, {**blobs.DEFAULTS, "min_area": 2})
    part = sample.sample(FOUND, paint.paint(narrow), "nest", "count")
    assert part["nest"][ELL] == 12 and part["nest"][SQUARE] == 0
    assert sample.sample(FOUND, paint.paint(narrow), "nest", "mean")["nest"][SQUARE] == 0.0
