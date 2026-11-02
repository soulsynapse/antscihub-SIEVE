"""paint: a table's records back into the mask they were found in, by contour or box; no records is empty."""
import numpy as np
import pytest

from tests.test_blobs import fed, m
from tests.test_track import table
from tools import blobs, paint

L = np.zeros((8, 8), np.uint8)
L[1:7, 1:3] = 255
L[5:7, 1:6] = 255


def test_painting_a_known_table_gives_back_the_mask_blobs_ran_on():
    found = blobs.run(fed(m), 0, {**blobs.DEFAULTS, "min_area": 2})
    kept = m.copy()
    kept[0, 11] = 0                                       # the speck under min_area
    assert np.array_equal(paint.paint(found, "contour"), kept) and np.array_equal(paint.paint(found, "box"), kept)
    assert paint.run(fed(found), 0, paint.DEFAULTS).dtype == np.uint8
    one = blobs.run(fed(L), 0, {**blobs.DEFAULTS, "min_area": 2})
    assert np.array_equal(paint.paint(one, "contour"), L)
    box = np.zeros_like(L)
    box[1:7, 1:6] = 255
    assert np.array_equal(paint.paint(one, "box"), box)
    assert paint.paint(found[:0], "contour").shape == m.shape and paint.paint(found[:0], "contour").max() == 0
    with pytest.raises(ValueError):
        paint.paint(table([(1, 1)]))
