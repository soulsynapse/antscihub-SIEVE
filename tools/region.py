"""Frame tool: the frame cut to the box of the chosen shape of a geometry file, or whole with none
chosen; a frame of any plane kind in, out as in at the cut's shape, with a button that cuts the video into a clip a shape, and the chosen
shape's clip served in its place once it is cut.

The file, written by a drawing utility and found by a `file` selector wired into `geometry`, is
JSON: `{"plate": [height, width], "shapes": [{"name": ..., "polygon": [[x, y], ...]} or
{"name": ..., "circle": [cx, cy, r]}, ...]}`, every number in plate pixels, a polygon's vertices
and a circle's extent within the plate's edges. A top-level key other than `plate` and `shapes`,
the drawing utility's own, is ignored, and the loader's answer is the same with it as without.
`load_geometry` raises on any other geometry, a shape past the edge, a repeated name or a
malformed file, saying what was wrong.

`choice`, empty or a name, chooses the cut: the chosen shape's box, or with none chosen, or a name
the file lacks, the whole plate. A box is the shape's extent, grown outward to even
pixels where the plate allows, so the clip H.264 writes is the cut served. A frame whose shape is
not the plate's raises with the two shapes, so a region wired after a rescale is seen and never
scaled, as does a file with no shapes. `pick` answers a click inside a shape, on a frame of the
plate's shape or of the cut's, with that name as the choice, or with empty when it is the choice
already; `draw` outlines the shapes on either frame. The card's Draw button opens the geometry
utility, `python -m utilities.geometry`, on the footage the node reads and the file wired into
`geometry`, in a process of its own; a save there reaches the region through the window's watch on
the file.

Cut writes a clip for every shape that has none, whatever is chosen, from the footage the node reads
in one ffmpeg pass, at `quality` and without sound, a frame out for each frame in, into the
player's store (tools/_cutfile.py); one under way when the card goes is cancelled. A clip is named
by its footage, its rect and its quality, so no clip is written over: a shape that moved, or another
quality, is a clip not yet cut, and the one it had stays until it is deleted. `quality` changes
nothing `run` hands out. `cut_file` is what the player serves in place of `run` while the node reads
the video node, or a node that serves a file, whose file is then the video cut: the clip of this
footage at the chosen shape's rect and the node's quality, while it is the size it landed at. A clip
cut at `standard` is H.264's rendering of the cut and not its pixels, so a served node hands out
other values than the same node run. The node's key is then the one a document opened on the clip
gives its video node, so everything after it is that document's. With no clip for the chosen shape,
or no shape chosen, the node cuts the frame as it did, and the card says which. The clip is of the
video file and not of what is wired into `in`, so the two differ where a node that serves no file
sits between the video and this one, and the player serves no clip there. `cut_files` is every clip
the node would serve under some choice; the card counts the store's clips of this footage that no
node of the document would, and deletes them on a press.

`table` is the shapes as a blobs table, one record each; no tool hands it out.
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

from tools._cutfile import QUALITIES, Cut, delete, folder_for, footage_of, landed, rect_key, unused, whole
from tools._draw import contour as draw_contour
from tools._table import moments, plane_dtype, with_column

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "region", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
DEFAULTS = {"plate": [], "shapes": [], "choice": "", "quality": "standard"}
PATHS = {"geometry": lambda path: load_geometry(path)}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # where `utilities` is found
MIN_ARC_POINTS = 16     # a circle's contour has at least this many vertices, and one per pixel of circumference past it
POLL_MS = 200


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


def rect(shape, plate):
    """(y0, y1, x0, x1) of `shape`'s box on a plate of (height, width), grown outward to even
    pixels where the plate allows."""
    if "circle" in shape:
        cx, cy, r = shape["circle"]
        xs, ys = (cx - r, cx + r), (cy - r, cy + r)
    else:
        xs, ys = zip(*shape["polygon"])

    def span(lo, hi, size):
        lo, hi = max(math.floor(lo), 0), min(math.floor(hi) + 1, size)
        return lo - lo % 2, min(hi + hi % 2, size)

    return (*span(min(ys), max(ys), plate[0]), *span(min(xs), max(xs), plate[1]))


def crops(params):
    """[(name, rect)] for every shape in `params`."""
    return [(s["name"], rect(s, params["plate"])) for s in params["shapes"]]


def served(params):
    """The rect `run` cuts: the chosen shape's, or the whole plate's when none is chosen or the
    choice names none; ValueError with no shapes."""
    found = crops(params)
    if not found:
        raise ValueError("no shapes; wire a file selector into geometry" if not params["plate"] else "the geometry file has no shapes")
    return dict(found).get(params["choice"]) or (0, params["plate"][0], 0, params["plate"][1])


def run(frames, row, params):
    plate = params["plate"]
    if not plate:
        raise ValueError("no geometry; wire a file selector into geometry")
    f = frames(row)
    if list(f.shape[:2]) != list(plate):
        raise ValueError(f"the frame is {f.shape[1]}x{f.shape[0]} and the file's plate {plate[1]}x{plate[0]}; "
                         "a region reads the plate, before any rescale or crop")
    y0, y1, x0, x1 = served(params)
    return np.ascontiguousarray(f[y0:y1, x0:x1])


def inside(point, shape):
    """Whether `point`, (x, y) in plate pixels, is on or inside `shape`."""
    x, y = point
    if "circle" in shape:
        cx, cy, r = shape["circle"]
        return math.hypot(x - cx, y - cy) <= r
    return cv2.pointPolygonTest(np.asarray(shape["polygon"], np.float32).reshape(-1, 1, 2), (float(x), float(y)), False) >= 0


def origin(shape, params):
    """(x, y) on the plate of the first pixel of a frame of `shape`, (height, width): the plate's
    own, or the cut `run` hands out; None for a frame that is neither."""
    if list(shape) == list(params["plate"]):
        return 0, 0
    try:
        y0, y1, x0, x1 = served(params)
    except ValueError:
        return None
    return (x0, y0) if list(shape) == [y1 - y0, x1 - x0] else None


def pick(point, shape, row, result, params):
    """The choice a click at `point` on a frame of `shape` means: the shape under it, or empty when
    that is the choice already; None off every shape or on a frame that is not the plate or the cut."""
    at = origin(shape, params)
    if at is None:
        return None
    point = (point[0] + at[0], point[1] + at[1])
    for s in reversed(params["shapes"]):
        if inside(point, s):
            return {"choice": "" if s["name"] == params["choice"] else s["name"]}
    return None


def draw(painter, row, result, start, params):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPen

    window = painter.window()
    at = origin((window.height(), window.width()), params)
    if at is None:
        return
    painter.save()
    painter.translate(-at[0], -at[1])
    painter.setBrush(Qt.NoBrush)
    for s in params["shapes"]:
        chosen = s["name"] == params["choice"]
        pen = QPen(QColor(255, 200, 80) if chosen else QColor(80, 220, 120), 0)
        pen.setCosmetic(True)
        pen.setWidth(3 if chosen else 0)
        painter.setPen(pen)
        draw_contour(painter, contour_of(s))
    painter.restore()


def utility_command(video, file):
    """The geometry utility's command line under the player's interpreter, with `--video` and `--file`
    for each that is not None."""
    argv = [sys.executable, "-m", "utilities.geometry"]
    for flag, path in (("--video", video), ("--file", file)):
        if path is not None:
            argv += [flag, os.path.abspath(path)]
    return argv


def launch(argv, cwd):
    """Starts `argv` in `cwd` and does not wait on it."""
    subprocess.Popen(argv, cwd=cwd)


def clip_of(video, footage, params):
    """(the clip of `video`, whose print is `footage`, at the chosen shape's rect and the params'
    quality, "") or (None, why there is none)."""
    choice, quality = params.get("choice"), params.get("quality", DEFAULTS["quality"])
    rect = dict(crops(params)).get(choice) if choice else None
    if not video or rect is None:
        return None, "a clip is one shape's; choose one"
    path = landed(folder_for(video, footage)).get(rect_key(footage, rect, quality))
    if path is None:
        return None, f"{choice} is not cut at {quality}"
    if not whole(path):
        return None, f"{os.path.basename(path)} is not the size it was cut at; delete it and cut again"
    return path, ""


def cut_file(video, footage, params):
    """`clip_of`'s clip, or None with no clip."""
    return clip_of(video, footage, params)[0]


def cut_files(video, footage, params):
    """Every clip in the store for a shape of `params` at their quality."""
    have, quality = landed(folder_for(video, footage)), params.get("quality", DEFAULTS["quality"])
    return [have[k] for _, rect in crops(params) if (k := rect_key(footage, rect, quality)) in have]


def settings(parent=None):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QProgressBar, QPushButton

    from sieve_player import ParamWidget
    from sieve_player.held import in_units
    from sieve_player.theme import readout

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.plate, self.shapes = list(DEFAULTS["plate"]), list(DEFAULTS["shapes"])
            self._get["plate"], self._set["plate"] = lambda: self.plate, lambda v: self._set_geometry(v, self.shapes)
            self._get["shapes"], self._set["shapes"] = lambda: self.shapes, lambda v: self._set_geometry(self.plate, v)
            self.video = self.file = self.cut = None
            self.in_use = ()
            running = self._running = []    # the Cut under way, reached by the slot below once this widget's own attributes are gone
            self.destroyed.connect(lambda: [cut.cancel() for cut in running])
            self.serving, self.clip = readout(), readout()
            self.chooser = self.add_list("choice", DEFAULTS["choice"])
            self.chooser.changed.connect(self._show)
            self.form.add_line(self.serving)
            self.draw, self.launched = QPushButton("Draw…"), readout()
            self.form.add_row("geometry", self.draw)
            self.form.add_line(self.launched)
            self.draw.clicked.connect(self._open_utility)
            self.add_choice("quality", QUALITIES, DEFAULTS["quality"])
            self.button, self.status = QPushButton("Cut"), readout()
            self.bar = QProgressBar()
            self.bar.setTextVisible(False)
            self.bar.hide()
            self.form.add_row("clips", self.button)
            self.form.add_line(self.clip)
            self.form.add_line(self.bar)
            self.form.add_line(self.status)
            self.button.clicked.connect(self._press)
            self.spare, self.sweep = readout(), QPushButton("Delete unused")
            self.form.add_line(self.spare)
            self.form.add_row("", self.sweep)
            self.sweep.clicked.connect(self._sweep)
            self.timer = QTimer(self)
            self.timer.setInterval(POLL_MS)
            self.timer.timeout.connect(self._poll)
            self._show()

        def set_source(self, path, fps):
            self.video = path
            self._show()

        def set_paths(self, paths):
            self.file = paths.get("geometry")

        def set_cut_files_in_use(self, paths):
            self.in_use = tuple(paths)
            self._show()    # the player asked the tools again: the store may be another, or hold other files

        def _unused(self):
            try:
                return unused(folder_for(self.video, footage_of(self.video)), self.in_use) if self.video else []
            except OSError:
                return []

        def _show_unused(self):
            found = self._unused()
            self.sweep.setVisible(bool(found))
            self.spare.setVisible(bool(found))
            if found:
                figure, unit = in_units(sum(n for _, _, n in found))
                self.spare.setText(f"{len(found)} clip{'s' if len(found) != 1 else ''} of this footage that no node of this document "
                                   f"would serve, {figure} {unit}; another document may use them")

        def _sweep(self):
            kept = delete([path for path, _, _ in self._unused()])
            self.status.setText("; ".join(f"{os.path.basename(p)} stays: {why}" for p, why in kept))
            self._show_unused()

        def _open_utility(self):
            try:
                launch(utility_command(self.video, self.file), ROOT)
            except OSError as e:
                self.launched.setText(f"the geometry utility did not start: {e}")
                return
            self.launched.setText("")

        def _set_geometry(self, plate, shapes):
            if (list(plate), list(shapes)) != (self.plate, self.shapes):
                self.plate, self.shapes = list(plate), list(shapes)
                self._show()
                self.changed.emit()

        def _show(self):
            p = self.params()
            names, choice = [s["name"] for s in self.shapes], p["choice"]
            if choice and choice not in names:
                status = f"{choice} is not in the file; the whole plate"
            elif choice:
                status = "chosen; click again for the whole plate"
            elif self.plate:
                status = f"plate {self.plate[1]}x{self.plate[0]}, {len(names)} shape{'s' if len(names) != 1 else ''}"
            else:
                status = "no geometry; wire a file selector into geometry"
            self.chooser.show([(n, n, "") for n in names], choice, status)
            self._show_unused()
            if not names:
                self.serving.setText("")
                self.clip.setText("")
                return
            y0, y1, x0, x1 = served(p)
            what = choice if choice in names else "the whole plate"
            self.serving.setText(f"serving {what}, {x1 - x0}x{y1 - y0} at {x0}, {y0}")
            try:
                path, why = clip_of(self.video, footage_of(self.video), p) if self.video else (None, "no video")
            except OSError as e:
                path, why = None, str(e)
            self.clip.setText(f"clip {os.path.basename(path)}" if path else f"no clip: {why}")

        def _press(self):
            if self.cut is not None:
                self.cut.cancel()
                self._poll()
                return
            if not self.video:
                self.status.setText("no video to cut")
                return
            try:
                p = self.params()
                self.cut = Cut(self.video, crops(p), p["quality"])
            except (ValueError, OSError) as e:
                self.status.setText(str(e))
                return
            self._running[:] = [self.cut]
            self.button.setText("Cancel")
            self.bar.setRange(0, self.cut.total)       # a count of 0 is Qt's busy bar
            self.bar.setValue(0)
            self.bar.show()
            self._progress()
            self.timer.start()

        def _progress(self):
            done, total, spent = self.cut.progress()
            self.bar.setValue(min(done, total))
            left = ""
            if 0 < done <= total:
                minutes = math.ceil(spent * (total - done) / done / 60)
                left = f", about {minutes} min left" if minutes > 1 else ", under a minute left"
            self.status.setText(f"cutting {self._clips()}, {self.cut.quality}: frame {done} of {total}{left}")

        def _clips(self):
            n = len(self.cut.todo)
            return f"{n} clip{'s' if n != 1 else ''}"

        def _poll(self):
            said = self.cut.poll()
            if said is None:
                self._progress()
                return
            self.timer.stop()
            self.bar.hide()
            self.status.setText(said or f"cut {self._clips()} into {self.cut.folder}")
            self.button.setText("Cut")
            self.cut = None
            self._running.clear()
            self._show()
            self.changed.emit()     # the params stand; the files they name have changed, and the player asks cut_file again

    return _Widget(parent)


if __name__ == "__main__":
    from sieve_player import play
    from tools import file

    sys.exit(play([file, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
