"""Frame tool: the frame cut to the box of a region's shape; a frame of any plane kind in and a
region on `regions`, out as in at the cut's shape, with a button that cuts the video into a clip a shape.

The region's plate, shapes and choice arrive as this node's params over the `regions` wire
(`PARAMS`), so choosing on the region, by its list or a click on the frame, chooses the cut here:
the chosen shape's box, or with none chosen the box around every shape. A box is the shape's
extent, grown outward to even pixels where the plate allows, so the clip H.264 writes is the cut
served. A frame of another shape than the plate
raises, as does a node with no shapes. Cut writes every shape, whatever is chosen, from the video
file itself in one ffmpeg pass, at `quality` as a bake's is and without sound, a frame out for each
frame in, to `<video>-crops/<name>.mp4`, with `crops.json` beside them holding each clip's place on
the plate. `quality` changes nothing served.
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
CRF = "18"          # the standard quality, as sieve_player/writers.py's
PRESET = "medium"
PART = ".part"
SAID_LINES = 5      # how much of ffmpeg's stderr a failure carries
POLL_MS = 200


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
    runs, then "" once every clip and crops.json have landed in `folder`, or what went wrong, with
    nothing left behind; `cancel()` stops it and leaves nothing. `progress()` is (frames written,
    the video's frames as its container counts them, seconds since the start). ValueError when two
    shapes would write one file or there is nothing to cut."""

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
        self.said = None

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
        self.log.seek(0)
        said = " | ".join(self.log.read().decode(errors="replace").strip().splitlines()[-SAID_LINES:])
        self.log.close()
        if code != 0:
            self._clear()
            self.said = f"ffmpeg exited {code}: {said}"
            return self.said
        try:
            os.remove(self.report)
            for p in self._parts():
                os.replace(p, p[:-len(PART)])
            with open(os.path.join(self.folder, "crops.json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump({"video": os.path.basename(self.video), "plate": self.plate, "quality": self.quality,
                           "crops": [{"name": name, "file": file_for(name), "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}
                                     for name, (y0, y1, x0, x1) in self.found]}, f, indent=1)
        except OSError as e:    # a clip open in a reader cannot be replaced on Windows
            self._clear()
            self.said = f"the clips did not land: {e}"
            return self.said
        self.said = ""
        return self.said

    def cancel(self):
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        if not self.log.closed:
            self.log.close()
        self._clear()
        self.said = "cancelled"


def settings(parent=None):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QProgressBar, QPushButton

    from sieve_player import ParamWidget
    from sieve_player.theme import readout

    class _Widget(ParamWidget):
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

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import file, region

    sys.exit(play([file, region, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
