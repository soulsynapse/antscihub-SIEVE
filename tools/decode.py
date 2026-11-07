"""Frame tool: the ArUco marker on each record read as a code and a heading; blobs in, a bgr or
gray plane on `plane`, blobs out with `prefix`_code and `prefix`_heading added.

Each record's box, grown by `margin` of its own width and height on every side, is cut from the
plane in the plane's coordinates and searched under `dictionary`; of the markers found, the one
whose centre lies nearest the record's centroid is the record's. The heading is the direction the
marker's top edge faces, in degrees from the x axis with y down as blobs' angle is, so an upright
marker reads -90 and one turned a quarter counterclockwise on screen reads 180. A record that
decodes to nothing reads NaN in both. The table must carry a plane and must not already have
either column.
"""
import math

import cv2
import numpy as np

from tools._table import draw as draw_table, plane as plane_of, with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "decode", "frame", "blobs", "blobs"
INPUTS = {"plane": ("bgr", "gray")}
DICTIONARIES = {name: getattr(cv2.aruco, f"DICT_{name.upper()}") for name in (
    "4x4_50", "4x4_100", "4x4_250", "4x4_1000", "5x5_50", "5x5_100", "5x5_250", "5x5_1000",
    "6x6_50", "6x6_100", "6x6_250", "6x6_1000", "7x7_50", "7x7_100", "7x7_250", "7x7_1000",
    "aruco_original", "apriltag_16h5", "apriltag_25h9", "apriltag_36h10", "apriltag_36h11")}
DEFAULTS = {"prefix": "tag", "dictionary": "4x4_50", "margin": 0.5}
MAX_MARGIN = 2.0


def detector(dictionary):
    if dictionary not in DICTIONARIES:
        raise ValueError(f"decode: no dictionary {dictionary!r}; one of {tuple(DICTIONARIES)}")
    return cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(DICTIONARIES[dictionary]),
                                   cv2.aruco.DetectorParameters())


def decode(table, plane, prefix="tag", dictionary="4x4_50", margin=0.5):
    det = detector(dictionary)
    shape = plane_of(table)
    if shape is None:
        raise ValueError("the table carries no plane to cut by")
    sy, sx = plane.shape[0] / shape[0], plane.shape[1] / shape[1]
    gray = plane if plane.ndim == 2 else cv2.cvtColor(plane, cv2.COLOR_BGR2GRAY)
    code, heading = np.full(len(table), np.nan), np.full(len(table), np.nan)
    for k, b in enumerate(table):
        x, y, w, h = (float(b[n]) for n in ("x", "y", "w", "h"))
        my, mx = margin * h, margin * w
        r0, r1 = max(math.floor((y - my) * sy), 0), min(math.ceil((y + h + my) * sy), gray.shape[0])
        c0, c1 = max(math.floor((x - mx) * sx), 0), min(math.ceil((x + w + mx) * sx), gray.shape[1])
        if r1 <= r0 or c1 <= c0:
            continue
        corners, ids, _ = det.detectMarkers(gray[r0:r1, c0:c1])
        if ids is None:
            continue
        centre = np.array([(b["cx"] + 0.5) * sx - 0.5 - c0, (b["cy"] + 0.5) * sy - 0.5 - r0])
        quads = [q[0] for q in corners]
        j = min(range(len(quads)), key=lambda i: np.sum((quads[i].mean(axis=0) - centre) ** 2))
        up = ((quads[j][0] + quads[j][1]) - (quads[j][2] + quads[j][3])) / 2 / (sx, sy)
        code[k], heading[k] = int(np.ravel(ids)[j]), math.degrees(math.atan2(up[1], up[0]))
    return with_column(with_column(table, f"{prefix}_code", code), f"{prefix}_heading", heading)


def run(frames, row, params):
    return decode(frames(row), frames(row, "plane"), params["prefix"], params["dictionary"], float(params["margin"]))


def draw(painter, row, result, start, params):
    draw_table(painter, result, params.get("outline", "box"), color=(240, 200, 80))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_text("prefix", DEFAULTS["prefix"])
    w.add_choice("dictionary", tuple(DICTIONARIES), DEFAULTS["dictionary"])
    w.add_float("margin", 0.0, MAX_MARGIN, DEFAULTS["margin"])
    return w
