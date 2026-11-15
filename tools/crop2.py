"""Frame tool: the frame cut to the box of a region's shape; a frame of any plane kind in and a
region on `regions`, out as in at the cut's shape, with a button that cuts the video into a clip a
shape, and the chosen shape's clip served in its place once it is cut.

The region's plate, shapes and choice arrive as this node's params over the `regions` wire
(`PARAMS`), so choosing on the region, by its list or a click on the frame, chooses the cut here:
the chosen shape's box, or with none chosen the box around every shape. A box is the shape's
extent, grown outward to even pixels where the plate allows, so the clip H.264 writes is the cut
served. A frame of another shape than the plate
raises, as does a node with no shapes. Cut writes every shape, whatever is chosen, from the video
file itself in one ffmpeg pass, at `quality` and without sound, a frame out for each frame in, to
`<video>-crops/<name>.mp4`, with `crops.json` beside them holding which footage they are of and each
clip's place on the plate. `quality` changes nothing `run` hands out.

`cut_file` is what the player serves in place of `run` while the node reads the video node: the
chosen shape's clip, once the record says it is of this footage at the rect the shape has now. The
node's key is then the one a document opened on the clip gives its video node, so everything after
it is that document's. A shape moved since the cut, or no shape chosen, and the node cuts the frame
as it did. The clip is of the video file and not of what is wired into `in`, so the two differ where
a node sits between the video and this one, and the player serves no clip there.
"""
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time

import cv2
import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "crop2", "frame", ("bgr", "gray", "mask", "hsv", "flow"), "same"
INPUTS = {"regions": "blobs"}
QUALITIES = ("lossless", "standard")
DEFAULTS = {"plate": [], "shapes": [], "choice": "", "quality": "standard"}
CRF = "18"          # the standard quality
PRESET = "medium"
PART = ".part"
SAID_LINES = 5      # how much of ffmpeg's stderr a failure carries
POLL_MS = 200
RECORD = "crops.json"
LAND_PATIENCE = 5.0 # s a finished cut waits on a clip a reader still has open, which Windows will not replace


def from_region(params):
    return {k: params.get(k, DEFAULTS[k]) for k in ("plate", "shapes", "choice")}


PARAMS = {"regions": from_region}


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
    """The rect `run` cuts: the chosen shape's, or the box around every shape's when none is chosen
    or the choice names none; ValueError with no shapes."""
    found = crops(params)
    if not found:
        raise ValueError("no shapes; wire a region into regions")
    rects = [r for name, r in found if name == params["choice"]] or [r for _, r in found]
    y0, y1, x0, x1 = zip(*rects)
    return min(y0), max(y1), min(x0), max(x1)


def run(frames, row, params):
    y0, y1, x0, x1 = served(params)
    f, plate = frames(row), params["plate"]
    if list(f.shape[:2]) != list(plate):
        raise ValueError(f"the frame is {f.shape[1]}x{f.shape[0]} and the region's plate {plate[1]}x{plate[0]}")
    return np.ascontiguousarray(f[y0:y1, x0:x1])


def folder_for(video):
    return os.path.splitext(str(video))[0] + "-crops"


def file_for(name):
    return re.sub(r"[^\w.-]", "_", name) + ".mp4"


_records, _prints = {}, {}      # path -> (what the file was when read, what was read): a sync asks cut_file again


def _stamp(path):
    st = os.stat(path)
    return st.st_size, st.st_mtime_ns


def record(folder):
    """What the Cut that last landed in `folder` wrote of its clips, or None with none there or one that does not read."""
    path = os.path.join(folder, RECORD)
    try:
        stamp = _stamp(path)
        if _records.get(path, (None,))[0] != stamp:
            with open(path, encoding="utf-8") as f:
                _records[path] = (stamp, json.load(f))
    except (OSError, ValueError):
        return None
    return _records[path][1]


def _print(path):
    from sieve_player.decoder import footage_print

    stamp = _stamp(path)
    if _prints.get(path, (None,))[0] != stamp:
        _prints[path] = (stamp, footage_print(path))
    return _prints[path][1]


def cut_file(video, footage, params):
    """(the clip a Cut of `video` wrote for the chosen shape, that clip's decoder.footage_print), or
    None: the record beside the clips must name the video, be of `footage`, the video's print, where
    it holds one, be of this plate, and hold the chosen shape at the rect it has now, and the clip
    must be there."""
    found = record(folder_for(video)) if video and params.get("choice") else None
    if (found is None or found.get("video") != os.path.basename(str(video)) or found.get("footage", footage) != footage
            or list(found.get("plate", ())) != list(params["plate"])):
        return None
    rect = dict(crops(params)).get(params["choice"])
    if rect is None:
        return None
    y0, y1, x0, x1 = rect
    for c in found.get("crops", ()):
        if c.get("name") == params["choice"] and [c.get(k) for k in "xywh"] == [x0, y0, x1 - x0, y1 - y0]:
            path = os.path.join(folder_for(video), c["file"])
            return (path, _print(path)) if os.path.isfile(path) else None
    return None


def command(video, folder, found, quality=DEFAULTS["quality"], progress=None):
    """ffmpeg's command line cutting `video` once into a part file per (name, rect) of `found` under
    `folder`, its progress report written to the file `progress` when one is named."""
    rate = ["-qp", "0"] if quality == QUALITIES[0] else ["-crf", CRF]
    argv = [shutil.which("ffmpeg") or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            *(["-progress", progress] if progress else []), "-i", str(video)]
    for name, (y0, y1, x0, x1) in found:
        argv += ["-map", "0:v:0", "-vf", f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}:exact=1", "-c:v", "libx264", *rate,
                 "-preset", PRESET, "-fps_mode", "passthrough", "-an", "-f", "mp4", os.path.join(folder, file_for(name) + PART)]
    return argv


class Cut:
    """One ffmpeg run cutting `video` into a clip per shape of `params`. `poll()` is None while it
    runs and while a clip it would replace is still open in a reader, then "" once every clip and
    the record have landed in `folder`, or what went wrong, with no part file left behind;
    `cancel()` stops it and leaves the folder as it was. The record is never of a clip it does not
    describe: the one there goes before the first clip lands and the new one is written after the
    last. `progress()` is (frames written, the video's frames as its container counts them, seconds
    since the start). ValueError when two shapes would write one file or there is nothing to cut."""

    def __init__(self, video, params):
        self.video, self.plate, self.quality = str(video), list(params["plate"]), str(params["quality"])
        self.found = crops(params)
        files = [file_for(name) for name, _ in self.found]
        if not files:
            raise ValueError("no shapes; wire a region into regions")
        if len(set(files)) != len(files):
            raise ValueError(f"two shapes would write one file: {sorted(f for f in set(files) if files.count(f) > 1)}")
        self.folder = folder_for(video)
        os.makedirs(self.folder, exist_ok=True)
        cap = cv2.VideoCapture(self.video)
        self.total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        self.log = tempfile.TemporaryFile()
        fd, self.report = tempfile.mkstemp(suffix=".progress")
        os.close(fd)
        self.t0, self.done = time.perf_counter(), 0
        self.proc = subprocess.Popen(command(video, self.folder, self.found, self.quality, self.report),
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=self.log)
        self.said, self.exited = None, None

    def progress(self):
        try:
            with open(self.report, "rb") as f:
                f.seek(max(0, os.path.getsize(self.report) - 1024))
                at = re.findall(rb"^frame=\s*(\d+)", f.read(), re.M)
            if at:
                self.done = int(at[-1])
        except OSError:
            pass
        return self.done, self.total, time.perf_counter() - self.t0

    def _parts(self):
        return [os.path.join(self.folder, file_for(name) + PART) for name, _ in self.found]

    def _clear(self):
        for p in (*self._parts(), self.report):
            if os.path.exists(p):
                os.remove(p)

    def poll(self):
        if self.said is not None:
            return self.said
        code = self.proc.poll()
        if code is None:
            return None
        if self.exited is None:
            self.exited = time.perf_counter()
            self.log.seek(0)
            said = " | ".join(self.log.read().decode(errors="replace").strip().splitlines()[-SAID_LINES:])
            self.log.close()
            if code != 0:
                self._clear()
                self.said = f"ffmpeg exited {code}: {said}"
                return self.said
        try:
            self._land()
        except OSError as e:
            if time.perf_counter() - self.exited < LAND_PATIENCE:
                return None
            self._clear()
            self.said = f"the clips did not land: {e}"
            return self.said
        self.said = ""
        return self.said

    def _land(self):
        from sieve_player.decoder import footage_print

        record = os.path.join(self.folder, RECORD)
        if os.path.exists(record):
            os.remove(record)
        for p in self._parts():
            if os.path.exists(p):
                os.replace(p, p[:-len(PART)])
        with open(record, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"video": os.path.basename(self.video), "footage": footage_print(self.video), "plate": self.plate,
                       "quality": self.quality,
                       "crops": [{"name": name, "file": file_for(name), "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}
                                 for name, (y0, y1, x0, x1) in self.found]}, f, indent=1)
        if os.path.exists(self.report):
            os.remove(self.report)

    def cancel(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        if not self.log.closed:
            self.log.close()
        self._clear()
        self.said = "cancelled"


def settings(parent=None):
    from PySide6.QtCore import QTimer, Signal
    from PySide6.QtWidgets import QProgressBar, QPushButton

    from sieve_player import ParamWidget
    from sieve_player.theme import readout

    class _Widget(ParamWidget):
        cutting = Signal(bool)      # a Cut began, or ended: while one runs the player serves none of this node's clips, so they can be replaced

        def __init__(self, parent=None):
            super().__init__(parent)
            self.held = {k: DEFAULTS[k] for k in PARAMS["regions"](DEFAULTS)}
            for k in self.held:
                self._get[k], self._set[k] = (lambda k=k: self.held[k]), (lambda v, k=k: self._hold(k, v))
            self.add_choice("quality", QUALITIES, DEFAULTS["quality"])
            self.serving = readout()
            self.form.add_line(self.serving)
            self.video, self.cut = None, None
            self.button, self.status = QPushButton("Cut"), readout()
            self.bar = QProgressBar()
            self.bar.setTextVisible(False)
            self.bar.hide()
            self.form.add_row("clips", self.button)
            self.form.add_line(self.bar)
            self.form.add_line(self.status)
            self.button.clicked.connect(self._press)
            self.timer = QTimer(self)
            self.timer.setInterval(POLL_MS)
            self.timer.timeout.connect(self._poll)
            self._show()

        def set_source(self, path, fps):
            self.video = path

        def _hold(self, k, v):
            if v != self.held[k]:
                self.held[k] = v
                self._show()
                self.changed.emit()

        def _show(self):
            p = self.params()
            if not p["shapes"]:
                self.serving.setText("no shapes; wire a region into regions")
                return
            y0, y1, x0, x1 = served(p)
            names = [s["name"] for s in p["shapes"]]
            what = p["choice"] if p["choice"] in names else f"all {len(names)} shapes"
            self.serving.setText(f"serving {what}, {x1 - x0}x{y1 - y0} at {x0}, {y0}; choose on the region")

        def _press(self):
            if self.cut is not None:
                self.cut.cancel()
                self._poll()
                return
            if not self.video:
                self.status.setText("no video to cut")
                return
            try:
                self.cut = Cut(self.video, self.params())
            except (ValueError, OSError) as e:
                self.status.setText(str(e))
                return
            self.cutting.emit(True)
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
            self.status.setText(f"cutting {len(self.cut.found)} clips, {self.cut.quality}: frame {done} of {total}{left}")

        def _poll(self):
            said = self.cut.poll()
            if said is None:
                self._progress()
                return
            self.timer.stop()
            self.bar.hide()
            self.status.setText(said or f"cut {len(self.cut.found)} clips into {self.cut.folder}")
            self.button.setText("Cut")
            self.cut = None
            self.cutting.emit(False)

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import file, region

    sys.exit(play([file, region, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
