"""decode: a marker drawn into a plane, found by blobs, reads its id and heading from bgr or gray; a
record over blank plane reads NaN; a plane of another shape is cut in its coordinates."""
import cv2
import numpy as np
import pytest

from tests.test_blobs import fed
from tools import blobs, decode

DICT = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)


def scene(turns=0, side=24):
    """A gray plane with marker 7 on white paper at (20, 30), turned `turns` quarters counterclockwise
    on screen, and a blank white patch at (90, 90); with the mask of the paper and the patch."""
    plane, mask = np.zeros((128, 128), np.uint8), np.zeros((128, 128), np.uint8)
    pad = side // 3
    paper = np.full((side + 2 * pad, side + 2 * pad), 255, np.uint8)
    paper[pad:pad + side, pad:pad + side] = np.rot90(cv2.aruco.generateImageMarker(DICT, 7, side), turns)
    plane[20:20 + paper.shape[0], 30:30 + paper.shape[1]] = paper
    plane[90:110, 90:110] = 255
    mask[20:20 + paper.shape[0], 30:30 + paper.shape[1]], mask[90:110, 90:110] = 255, 255
    return plane, mask


PLANE, MASK = scene()
FOUND = blobs.run(fed(MASK), 0, {**blobs.DEFAULTS, "min_area": 2})
TAG, BLANK = list(FOUND["x"]).index(30), list(FOUND["x"]).index(90)


def turned(h, by):
    return abs(((h - by + 180) % 360) - 180)


def test_a_marker_reads_its_id_and_heading_and_a_blank_record_reads_none():
    for plane in (PLANE, cv2.cvtColor(PLANE, cv2.COLOR_GRAY2BGR)):
        out = decode.run(fed(FOUND, plane), 0, decode.DEFAULTS)
        assert out.dtype.names[-2:] == ("tag_code", "tag_heading") and blobs.plane(out) == PLANE.shape
        assert out["tag_code"][TAG] == 7 and turned(out["tag_heading"][TAG], -90) < 1
        assert np.isnan(out["tag_code"][BLANK]) and np.isnan(out["tag_heading"][BLANK])
    for turns, heading in ((1, 180), (2, 90), (3, 0)):
        assert turned(decode.decode(FOUND, scene(turns)[0])["tag_heading"][TAG], heading) < 1
    assert np.isnan(decode.decode(FOUND, np.zeros_like(PLANE))["tag_code"]).all()
    with pytest.raises(ValueError):
        decode.decode(FOUND, PLANE, dictionary="3x3_50")
    with pytest.raises(ValueError):
        decode.decode(decode.decode(FOUND, PLANE), PLANE)


def test_a_plane_of_another_shape_is_cut_in_its_coordinates():
    twice = cv2.resize(PLANE, (256, 256), interpolation=cv2.INTER_NEAREST)
    half = cv2.resize(PLANE, (64, 64), interpolation=cv2.INTER_NEAREST)
    for plane in (twice, half):
        out = decode.decode(FOUND, plane)
        assert out["tag_code"][TAG] == 7 and turned(out["tag_heading"][TAG], -90) < 1 and np.isnan(out["tag_code"][BLANK])
    assert decode.decode(FOUND, cv2.resize(scene(1)[0], (256, 256), interpolation=cv2.INTER_NEAREST))["tag_heading"][TAG] == pytest.approx(180, abs=1)
