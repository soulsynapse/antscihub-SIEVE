"""region: a geometry file's shapes as one STATIC table, each record a filled shape with its name, the
choice narrowing to one, a frame that is not the plate refused, and a click inside a shape picking it."""
import json
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sieve_player import document as D  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from tests.test_graph import Dec, tool  # noqa: E402
from tests.test_blobs import fed  # noqa: E402
from tests.test_track import table as points  # noqa: E402
from tools import attach, blobs_to_mask, filter as filter_, region, rescale, sample  # noqa: E402
from tools._table import plane, plane_dtype  # noqa: E402

H, W = 40, 60
SQUARE = [[20, 10], [30, 20], [20, 30], [10, 20]]          # a square turned 45 degrees, diagonal 20
CIRCLE = [45.0, 20.0, 8.0]
GEOMETRY = {"plate": [H, W], "shapes": [{"name": "nest", "polygon": SQUARE}, {"name": "dish", "circle": CIRCLE}]}


def write(tmp_path, d, name="geometry.json"):
    p = tmp_path / name
    p.write_text(json.dumps(d), encoding="utf-8")
    return str(p)


def params(choice=""):
    return {"plate": [H, W], "shapes": GEOMETRY["shapes"], "choice": choice}


def frame(shape=(H, W)):
    return np.zeros(shape, np.uint8)


def test_the_loader_reads_a_polygon_and_a_circle_and_refuses_what_is_not_one(tmp_path):
    got = region.load_geometry(write(tmp_path, GEOMETRY))
    assert got["plate"] == [H, W] and [s["name"] for s in got["shapes"]] == ["nest", "dish"]
    assert got["shapes"][0]["polygon"] == [[float(x), float(y)] for x, y in SQUARE] and got["shapes"][1]["circle"] == CIRCLE
    twice = {"plate": [H, W], "shapes": [{"name": "t", "polygon": [[1, 1], [5, 1], [3, 4]]}, {"name": "t", "polygon": [[1, 1], [5, 1], [3, 4]]}]}
    with pytest.raises(ValueError, match="two shapes are named 't'"):
        region.load_geometry(write(tmp_path, twice))
    past = {"plate": [H, W], "shapes": [{"name": "far", "circle": [W - 2, 20, 5]}]}
    with pytest.raises(ValueError, match="past the plate's 60x40"):
        region.load_geometry(write(tmp_path, past))
    other = {"plate": [H, W], "shapes": [{"name": "r", "rect": [1, 1, 5, 5]}]}
    with pytest.raises(ValueError, match="not a polygon or a circle"):
        region.load_geometry(write(tmp_path, other))
    with pytest.raises(ValueError, match="plate"):
        region.load_geometry(write(tmp_path, {"plate": [H], "shapes": []}))
    with pytest.raises(ValueError, match="three or more"):
        region.load_geometry(write(tmp_path, {"plate": [H, W], "shapes": [{"name": "line", "polygon": [[1, 1], [5, 5]]}]}))


def test_each_shape_is_a_filled_record_the_mask_paints_back_and_the_tools_read():
    import cv2

    out = region.run(fed(frame()), 0, params())
    assert len(out) == 2 and plane(out) == (H, W) and out["name"].tolist() == ["nest", "dish"]
    painted = blobs_to_mask.mask(out[out["name"] == "nest"], "contour")
    fill = np.zeros((H, W), np.uint8)
    cv2.fillPoly(fill, [np.array(SQUARE, np.int32).reshape(-1, 1, 2)], 255)
    assert np.array_equal(painted, fill)
    nest = out[0]
    assert (nest["x"], nest["y"], nest["w"], nest["h"]) == (10, 10, 21, 21) and nest["area"] == np.count_nonzero(fill)
    assert abs(nest["cx"] - 20) < 0.01 and abs(nest["cy"] - 20) < 0.01 and nest["contour"].tolist() == SQUARE
    cx, cy, r = CIRCLE
    dish = out[1]
    ring = 2 * np.pi * r
    assert abs(dish["area"] - np.pi * r * r) < ring and abs(dish["cx"] - cx) < 0.1 and abs(dish["cy"] - cy) < 0.1
    assert abs(np.count_nonzero(blobs_to_mask.mask(out[1:], "contour")) - np.pi * r * r) < ring
    assert abs(dish["major"] - dish["minor"]) < 0.5
    # the ants' columns land on the region each sits in, as attach relates two tables: here one inside the nest, one outside
    ants = points([(20, 20), (50, 5)]).astype(plane_dtype((H, W)))
    on = attach.attach(out, ants, "ant")
    assert on["ant_n"].tolist() == [1, 0] and on["ant_cx"][0] == 20.0 and np.isnan(on["ant_cx"][1]) and on["name"].tolist() == ["nest", "dish"]
    counted = sample.sample(out, fill, "fill", "count")
    assert counted["fill"].tolist() == [nest["area"], 0]
    assert filter_.keep(out, "area", "", str(nest["area"]))["name"].tolist() == ["nest"]


def test_the_choice_narrows_to_one_record_a_missing_name_reads_as_every_shape_and_a_click_picks():
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication([])
    assert region.run(fed(frame()), 0, params("dish"))["name"].tolist() == ["dish"]
    assert region.run(fed(frame()), 0, params(""))["name"].tolist() == ["nest", "dish"]
    assert region.run(fed(frame()), 0, params("gone"))["name"].tolist() == ["nest", "dish"]
    w = region.settings()
    w.set_params(params("gone"))
    assert "gone is not in the file" in w.chooser.status.text()
    w.set_params(params("dish"))
    assert [w.chooser.list.item(i).text() for i in range(w.chooser.list.count())] == ["   nest", "● dish"]
    changed = []
    w.changed.connect(lambda: changed.append(w.params()["choice"]))
    w.chooser.list.itemClicked.emit(w.chooser.list.item(1))
    w.chooser.list.itemClicked.emit(w.chooser.list.item(0))
    assert changed == ["", "nest"] and w.params()["plate"] == [H, W] and w.params()["shapes"] == params()["shapes"]
    result = region.run(fed(frame()), 0, params())
    assert region.pick((20, 20), (H, W), 0, result, params()) == {"choice": "nest"}
    assert region.pick((20, 20), (H, W), 0, result, params("nest")) == {"choice": ""}
    assert region.pick((45, 20), (H, W), 0, result, params("nest")) == {"choice": "dish"}
    assert region.pick((2, 2), (H, W), 0, result, params()) is None
    assert region.pick((10, 10), (H // 2, W // 2), 0, result, params()) is None


def test_a_frame_of_another_shape_than_the_plate_is_refused_and_said():
    bgr = tool("bgr", "bgr", "bgr", lambda f, p: np.zeros((H, W, 3), np.uint8))
    tools = {t.NAME: t for t in (bgr, rescale, region)}
    doc = D.from_tools([bgr, rescale, region])
    doc.node("region").params.update(params())
    doc.node("rescale").params["scale"] = 0.5
    g = Graph(doc, Dec(), tools)
    assert g.source("region") == "rescale"
    with pytest.raises(ValueError) as e:
        g.compute("region", 0)
    assert e.value.sieve_node == "region" and "the frame is 30x20 and the file's plate 60x40" in g.standing("region")
    doc.connect("bgr", "region")
    g.sync()
    assert g.standing("region") == "" and len(g.compute("region", 0)) == 2 and len(g.compute("region", 5)) == 2
    assert region.STATIC and g.entry("region").static
    doc.node("region").params["plate"] = []
    g.sync()
    with pytest.raises(ValueError, match="no geometry"):
        g.compute("region", 0)
