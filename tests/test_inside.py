"""inside: the region whose contour, or box, holds a record's centroid is written onto the record,
the smallest when several do, None and NaN under none, with the count; regions found at another
shape are placed in the records' coordinates."""
import numpy as np
import pytest

from tests.test_blobs import fed
from tests.test_track import table as points
from tools import inside, region
from tools._table import plane, plane_dtype

H, W = 40, 60
YARD = {"name": "yard", "polygon": [[5, 5], [55, 5], [55, 35], [5, 35]]}
NEST = {"name": "nest", "circle": [20.0, 20.0, 6.0]}
DISH = {"name": "dish", "polygon": [[36, 12], [48, 12], [48, 28], [36, 28]]}
REGIONS = region.table([H, W], [YARD, NEST, DISH])
IN_NEST, IN_DISH, IN_YARD, OUTSIDE = (20, 20), (42, 20), (10, 30), (2, 2)


def ants(pts, shape=(H, W)):
    return points(pts).astype(plane_dtype(shape))


def test_each_record_reads_the_smallest_region_holding_it_and_none_reads_nothing():
    out = inside.run(fed(ants([IN_NEST, OUTSIDE]), REGIONS), 0, inside.DEFAULTS)
    assert out.dtype.names[-2:] == ("region_name", "region_n") and plane(out) == (H, W) and len(out) == 2
    assert out["region_name"].tolist() == ["nest", None] and out["region_n"].tolist() == [2, 0]
    full = inside.inside(ants([IN_NEST, IN_DISH, IN_YARD, OUTSIDE]), REGIONS, "r", ["area"])
    assert full["r_name"].tolist() == ["nest", "dish", "yard", None] and full["r_n"].tolist() == [2, 2, 1, 0]
    nest, dish, yard = (REGIONS["area"][REGIONS["name"] == n][0] for n in ("nest", "dish", "yard"))
    assert full["r_area"].tolist()[:3] == [nest, dish, yard] and np.isnan(full["r_area"][3])
    boxed = inside.inside(ants([(15, 15)]), REGIONS, "r", outline="box")
    assert inside.inside(ants([(15, 15)]), REGIONS, "r")["r_name"].tolist() == ["yard"] and boxed["r_name"].tolist() == ["nest"]
    with pytest.raises(ValueError, match="no column 'hue'"):
        inside.inside(ants([IN_NEST]), REGIONS, "r", ["hue"])
    with pytest.raises(ValueError, match="already has a column"):
        inside.inside(out, REGIONS, "region")


def test_regions_found_at_another_shape_are_placed_in_the_records_coordinates():
    half = inside.inside(ants([(10, 10), (21, 10), (1, 1)], (H // 2, W // 2)), REGIONS, "r")
    assert half["r_name"].tolist() == ["nest", "dish", None] and half["r_n"].tolist() == [2, 2, 0]
    unplaced = points([IN_NEST])
    with pytest.raises(ValueError, match="no plane"):
        inside.inside(unplaced, REGIONS)
