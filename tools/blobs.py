"""Frame tool: the connected regions of a mask, each a row of a table; mask or gray in, blobs out.

Foreground is every nonzero pixel, so a mask from threshold or inrange, a black-and-white image,
or a difference plane all read the same way. Regions are 8-connected. `min_area` drops the
speckle under it and `max_area`, when above zero, drops anything over it, both in pixels. The
output is a 1-D structured array, one record per region kept: `x`, `y`, `w`, `h` the box, `area`
the pixel count, `cx`, `cy` the centroid; empty when nothing is kept. It is not an image, so the
display shows what this node read with each box drawn over it.
"""
import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "blobs", "frame", ("mask", "gray"), "blobs"
DEFAULTS = {"min_area": 50, "max_area": 0}
MAX_AREA = 100000
DTYPE = np.dtype([(n, np.float32) for n in ("x", "y", "w", "h", "area", "cx", "cy")])


def find(mask, min_area, max_area=0):
    fg = (np.asarray(mask) != 0).astype(np.uint8)
    n, _, stats, centroids = cv2.connectedComponentsWithStats(fg, connectivity=8)
    out = np.empty(max(n - 1, 0), DTYPE)
    if n > 1:
        s, c = stats[1:], centroids[1:]      # label 0 is the background
        out["x"], out["y"] = s[:, cv2.CC_STAT_LEFT], s[:, cv2.CC_STAT_TOP]
        out["w"], out["h"] = s[:, cv2.CC_STAT_WIDTH], s[:, cv2.CC_STAT_HEIGHT]
        out["area"], out["cx"], out["cy"] = s[:, cv2.CC_STAT_AREA], c[:, 0], c[:, 1]
    keep = out["area"] >= min_area
    if max_area > 0:
        keep &= out["area"] <= max_area
    return out[keep]


def run(frames, row, params):
    return find(frames(row), int(params["min_area"]), int(params["max_area"]))


def draw(painter, row, result, start):
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QPen

    if result is None or len(result) == 0:
        return
    pen = QPen(QColor(80, 220, 120), 0)      # width 0: one device pixel at any zoom
    pen.setCosmetic(True)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    for b in result:
        painter.drawRect(QRectF(float(b["x"]), float(b["y"]), float(b["w"]), float(b["h"])))


def settings(parent=None):
    from sieve_player import ParamWidget  # only the GUI needs the player

    w = ParamWidget(parent)
    w.add_int("min_area", 0, MAX_AREA, DEFAULTS["min_area"])
    w.add_int("max_area", 0, MAX_AREA, DEFAULTS["max_area"])
    return w


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, threshold

    sys.exit(play([gray, threshold, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
