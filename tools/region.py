"""Frame tool: the shapes of a geometry file as a table, one record each, the same at every row; a
frame of any plane kind in for its shape, blobs out.

The file, written by a drawing utility and found by a `file` selector wired into `geometry`, is
JSON: `{"plate": [height, width], "shapes": [{"name": ..., "polygon": [[x, y], ...]} or
{"name": ..., "circle": [cx, cy, r]}, ...]}`, every number in plate pixels, a polygon's vertices
and a circle's extent within the plate's edges. A top-level key other than `plate` and `shapes`,
the drawing utility's own, is ignored, and the loader's answer is the same with it as without.
`load_geometry` raises on any other geometry, a shape past the edge, a repeated name or a
malformed file, saying what was wrong. A record is the
filled shape's position and moment columns, its outline as `contour` and its name in `name`;
`choice`, empty or a name, narrows the table to that record, and a name the file lacks reads as
empty. A frame whose shape is not the plate's raises with the two shapes, so a region wired after
a rescale or a crop is seen and never scaled. `pick` answers a click on a frame of the plate's
shape inside a shape with that name as the choice, or with empty when it is the choice already.
"""
import json
import math

import cv2
import numpy as np

from tools._draw import outline as draw_outline
from tools._table import moments, plane_dtype, with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "region", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "blobs"
STATIC = True
DEFAULTS = {"plate": [], "shapes": [], "choice": ""}
PATHS = {"geometry": lambda path: load_geometry(path)}
MIN_ARC_POINTS = 16     # a circle's contour has at least this many vertices, and one per pixel of circumference past it


def _number(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(f"{what} is {v!r}, not a number")
    return float(v)


def _shape(d, i, h, w):
    """One shape of the file as the params hold it, checked: a name, and a polygon or a circle inside the plate."""
    if not isinstance(d, dict) or "name" not in d:
        raise ValueError(f"shape {i} has no name")
    name = d["name"]
    if not isinstance(name, str) or not name:
        raise ValueError(f"shape {i} has the name {name!r}, not a word")
    kinds = [k for k in ("polygon", "circle") if k in d]
    if len(kinds) != 1 or set(d) - {"name", kinds[0]}:
        raise ValueError(f"{name} is not a polygon or a circle: its keys are {sorted(d)}")
    if kinds[0] == "polygon":
        pts = d["polygon"]
        if not isinstance(pts, list) or len(pts) < 3 or any(not isinstance(p, list) or len(p) != 2 for p in pts):
            raise ValueError(f"{name}'s polygon is not three or more [x, y] vertices")
        pts = [[_number(x, f"{name}'s vertex {k} x"), _number(y, f"{name}'s vertex {k} y")] for k, (x, y) in enumerate(pts)]
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        box = (min(xs), min(ys), max(xs), max(ys))
        out = {"name": name, "polygon": pts}
    else:
        c = d["circle"]
        if not isinstance(c, list) or len(c) != 3:
            raise ValueError(f"{name}'s circle is not [cx, cy, r]")
        cx, cy, r = (_number(v, f"{name}'s circle {k}") for k, v in zip(("cx", "cy", "r"), c))
        if r <= 0:
            raise ValueError(f"{name}'s radius is {r}, not positive")
        box = (cx - r, cy - r, cx + r, cy + r)
        out = {"name": name, "circle": [cx, cy, r]}
    if box[0] < 0 or box[1] < 0 or box[2] > w or box[3] > h:
        raise ValueError(f"{name} reaches x {box[0]:g}-{box[2]:g}, y {box[1]:g}-{box[3]:g}, past the plate's {w}x{h}")
    return out


def load_geometry(path):
    """Params from a geometry file: `plate` as [height, width] and `shapes` as the file has them,
    checked. Raises ValueError on a malformed file with what was wrong."""
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict) or "plate" not in d or "shapes" not in d:
        raise ValueError("a geometry file has a plate and shapes")
    plate = d["plate"]
    if not isinstance(plate, list) or len(plate) != 2 or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in plate):
        raise ValueError(f"the plate is {plate!r}, not [height, width] in pixels")
    if not isinstance(d["shapes"], list):
        raise ValueError("shapes is not a list")
    h, w = plate
    shapes, seen = [], set()
    for i, s in enumerate(d["shapes"]):
        shape = _shape(s, i, h, w)
        if shape["name"] in seen:
            raise ValueError(f"two shapes are named {shape['name']!r}")
        seen.add(shape["name"])
        shapes.append(shape)
    return {"plate": [h, w], "shapes": shapes}


def contour_of(shape):
    """A shape's outline as blobs holds one: (N, 2) int32 x, y. A circle is sampled one vertex a
    pixel of circumference, so its fill is the circle's to within a pixel ring."""
    if "polygon" in shape:
        return np.rint(np.asarray(shape["polygon"], np.float64)).astype(np.int32)
    cx, cy, r = shape["circle"]
    n = max(MIN_ARC_POINTS, math.ceil(2 * math.pi * r))
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return np.rint(np.stack([cx + r * np.cos(t), cy + r * np.sin(t)], axis=1)).astype(np.int32)


def table(plate, shapes, choice=""):
    """One record per shape at the plate's shape, each the filled outline's columns with `name` on
    it; narrowed to the one named by `choice` when it names one."""
    h, w = plate
    out = np.empty(len(shapes), plane_dtype((h, w)))
    for k, s in enumerate(shapes):
        contour = contour_of(s)
        contour[:, 0], contour[:, 1] = np.clip(contour[:, 0], 0, w - 1), np.clip(contour[:, 1], 0, h - 1)
        x, y = (int(v) for v in contour.min(axis=0))
        bw, bh = (int(v) + 1 for v in contour.max(axis=0) - (x, y))
        local = np.zeros((bh, bw), np.uint8)
        cv2.fillPoly(local, [(contour - (x, y)).reshape(-1, 1, 2)], 1)
        inside = local.astype(bool)
        cx, cy, angle, major, minor = moments(inside)
        r = out[k]
        r["x"], r["y"], r["w"], r["h"], r["area"] = x, y, bw, bh, int(np.count_nonzero(inside))
        r["cx"], r["cy"], r["angle"], r["major"], r["minor"] = x + cx, y + cy, angle, major, minor
        r["mean"], r["peak"], r["core"], r["contour"] = np.nan, np.nan, -1, contour
    out = with_column(out, "name", np.array([s["name"] for s in shapes], dtype=str))
    return out[out["name"] == choice] if choice and choice in out["name"] else out


def run(frames, row, params):
    plate = params["plate"]
    if not plate:
        raise ValueError("no geometry; wire a file selector into geometry")
    shape = tuple(frames(row).shape[:2])
    if shape != tuple(plate):
        raise ValueError(f"the frame is {shape[1]}x{shape[0]} and the file's plate {plate[1]}x{plate[0]}; "
                         "a region reads the plate, before any rescale or crop")
    return table(plate, params["shapes"], params["choice"])


def inside(point, shape):
    """Whether `point`, (x, y) in plate pixels, is on or inside `shape`."""
    x, y = point
    if "circle" in shape:
        cx, cy, r = shape["circle"]
        return math.hypot(x - cx, y - cy) <= r
    return cv2.pointPolygonTest(np.asarray(shape["polygon"], np.float32).reshape(-1, 1, 2), (float(x), float(y)), False) >= 0


def pick(point, shape, row, result, params):
    """The choice a click at `point` on a frame of `shape` means: the shape under it, or empty when
    that is the choice already; None off every shape or on a frame that is not the plate."""
    if list(shape) != list(params["plate"]):
        return None
    for s in reversed(params["shapes"]):
        if inside(point, s):
            return {"choice": "" if s["name"] == params["choice"] else s["name"]}
    return None


def draw(painter, row, result, start, params):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPen

    painter.setBrush(Qt.NoBrush)
    for s in params["shapes"]:
        chosen = s["name"] == params["choice"]
        pen = QPen(QColor(255, 200, 80) if chosen else QColor(80, 220, 120), 0)
        pen.setCosmetic(True)
        pen.setWidth(3 if chosen else 0)
        painter.setPen(pen)
        draw_outline(painter, {"contour": contour_of(s)}, "contour")


def settings(parent=None):
    from sieve_player import ParamWidget

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.plate, self.shapes = list(DEFAULTS["plate"]), list(DEFAULTS["shapes"])
            self._get["plate"], self._set["plate"] = lambda: self.plate, lambda v: self._set_geometry(v, self.shapes)
            self._get["shapes"], self._set["shapes"] = lambda: self.shapes, lambda v: self._set_geometry(self.plate, v)
            self.chooser = self.add_list("choice", DEFAULTS["choice"])
            self.chooser.changed.connect(self._show)
            self._show()

        def _set_geometry(self, plate, shapes):
            if (list(plate), list(shapes)) != (self.plate, self.shapes):
                self.plate, self.shapes = list(plate), list(shapes)
                self._show()
                self.changed.emit()

        def _show(self):
            names, choice = [s["name"] for s in self.shapes], self.chooser.value
            if choice and choice not in names:
                status = f"{choice} is not in the file; every shape"
            elif choice:
                status = "chosen; click again for every shape"
            elif self.plate:
                status = f"plate {self.plate[1]}x{self.plate[0]}, {len(names)} shape{'s' if len(names) != 1 else ''}"
            else:
                status = "no geometry; wire a file selector into geometry"
            self.chooser.show([(n, n, "") for n in names], choice, status)

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import blobs_to_mask, file

    sys.exit(play([file, sys.modules[__name__], blobs_to_mask], sys.argv[1] if len(sys.argv) > 1 else None))
