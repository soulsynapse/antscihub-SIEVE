"""attach: a mark's columns land on the animal whose contour, or box, holds its centroid; none reads
NaN and several the largest with a count; marks found at another shape attach in the animals'
coordinates."""
import numpy as np
import pytest

from tests.test_blobs import fed
from tools import attach, blobs

M = np.zeros((8, 8), np.uint8)
M[1:7, 1:3] = 255
M[5:7, 1:6] = 255                        # an L, 18 px
M[1:3, 5:7] = 255                        # a square, 4 px
M[5:7, 7:8] = 255                        # a bar below it, 2 px, under no dot
ANIMALS = blobs.run(fed(M), 0, {**blobs.DEFAULTS, "min_area": 2})
ELL, SQUARE, BAR = (list(ANIMALS["area"]).index(a) for a in (18, 4, 2))


def dots(points, shape):
    """A marks table with cx, cy, area and a hue column, found in a plane of `shape`."""
    t = np.zeros(len(points), blobs.plane_dtype(shape, np.dtype(blobs.DTYPE.descr + [("hue", np.int32)])))
    for i, (cx, cy, area, hue) in enumerate(points):
        t["cx"][i], t["cy"][i], t["area"][i], t["hue"][i] = cx, cy, area, hue
    return t


DOTS = dots([(1.0, 3.0, 3, 10), (5.0, 1.0, 2, 20), (6.0, 2.0, 5, 30), (4.0, 2.0, 7, 40)], M.shape)   # the last is in the L's box, off the L


def test_each_dots_columns_land_on_the_animal_under_it():
    out = attach.run(fed(ANIMALS, DOTS), 0, {"prefix": "dot", "columns": "hue", "outline": "contour"})
    assert out.dtype.names[-5:] == ("dot_cx", "dot_cy", "dot_area", "dot_hue", "dot_n") and blobs.plane(out) == M.shape
    assert (out["dot_cx"][ELL], out["dot_cy"][ELL], out["dot_area"][ELL], out["dot_hue"][ELL], out["dot_n"][ELL]) == (1.0, 3.0, 3, 10, 1)
    assert (out["dot_cx"][SQUARE], out["dot_area"][SQUARE], out["dot_hue"][SQUARE], out["dot_n"][SQUARE]) == (6.0, 5, 30, 2)
    assert np.isnan(out["dot_hue"][BAR]) and np.isnan(out["dot_cx"][BAR]) and out["dot_n"][BAR] == 0
    boxed = attach.attach(ANIMALS, DOTS, "dot", ["hue"], "box")
    assert (boxed["dot_hue"][ELL], boxed["dot_n"][ELL]) == (40, 2)
    with pytest.raises(ValueError):
        attach.attach(ANIMALS, DOTS, "dot", ["contour"])
    with pytest.raises(ValueError):
        attach.attach(ANIMALS, DOTS, "dot", ["tint"])
    with pytest.raises(ValueError):
        attach.attach(out, DOTS, "dot")


def test_marks_found_at_twice_the_shape_attach_in_the_animals_coordinates():
    big = dots([(2.5, 6.5, 12, 10), (10.5, 2.5, 8, 20), (12.5, 4.5, 20, 30)], (16, 16))
    out = attach.attach(ANIMALS, big, "dot", ["hue"])
    assert (out["dot_cx"][ELL], out["dot_cy"][ELL], out["dot_area"][ELL], out["dot_hue"][ELL]) == (1.0, 3.0, 12, 10)
    assert (out["dot_cx"][SQUARE], out["dot_cy"][SQUARE], out["dot_hue"][SQUARE], out["dot_n"][SQUARE]) == (6.0, 2.0, 30, 2)
    assert out["dot_n"][BAR] == 0
    small = dots([(0.0, 1.0, 1, 10)], (4, 4))                              # full pixel (1, 3), in the L
    assert attach.attach(ANIMALS, small, "dot")["dot_n"].tolist()[ELL] == 1
