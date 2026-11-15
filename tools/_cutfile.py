"""The clips a cutting tool writes beside a video and the record of them: where they lie, the one
ffmpeg run that writes them, and what the record says once they have landed. Not a tool; a tool
imports it and no other tool (tests/test_seams.py).

`<video>-crops/<name>.mp4` is a clip, and `crops.json` beside them says which footage they are of,
the plate, the quality and each clip's file, place on the plate and size in bytes. The record is
never of a clip it does not describe: the one there goes before the first clip lands and the new
one is written after the last.
"""
import atexit
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import weakref

import cv2

QUALITIES = ("lossless", "standard")
CRF = "18"          # the standard quality
PRESET = "medium"
PART = ".part"
SAID_LINES = 5      # how much of ffmpeg's stderr a failure carries
RECORD = "crops.json"
LAND_PATIENCE = 5.0 # s a finished cut waits on a clip a reader still has open, which Windows will not replace


def folder_for(video):
    return os.path.splitext(str(video))[0] + "-crops"


def file_for(name):
    return re.sub(r"[^\w.-]", "_", name) + ".mp4"


_records, _prints = {}, {}      # path -> (what the file was when read, what was read)


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


def footage_of(path):
    """decoder.footage_print of the file at `path`, read again only when its size or mtime moved; OSError with no file."""
    from sieve_player.decoder import footage_print

    stamp = _stamp(path)
    if _prints.get(path, (None,))[0] != stamp:
        _prints[path] = (stamp, footage_print(path))
    return _prints[path][1]


def command(video, folder, found, quality=QUALITIES[1], progress=None):
    """ffmpeg's command line cutting `video` once into a part file per (name, rect) of `found` under
    `folder`, its progress report written to the file `progress` when one is named."""
    rate = ["-qp", "0"] if quality == QUALITIES[0] else ["-crf", CRF]
    argv = [shutil.which("ffmpeg") or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            *(["-progress", progress] if progress else []), "-i", str(video)]
    for name, (y0, y1, x0, x1) in found:
        argv += ["-map", "0:v:0", "-vf", f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}:exact=1", "-c:v", "libx264", *rate,
                 "-preset", PRESET, "-fps_mode", "passthrough", "-an", "-f", "mp4", os.path.join(folder, file_for(name) + PART)]
    return argv


_running = weakref.WeakSet()    # the Cuts whose ffmpeg may still run: one the player leaves behind is stopped as it exits


@atexit.register
def _stop_running():
    for cut in list(_running):
        cut.cancel()


class Cut:
    """One ffmpeg run cutting `video` into a clip per (name, rect) of `found`, rects as (y0, y1, x0,
    x1) on `plate`, at `quality`. `poll()` is None while it runs and while a clip it would replace
    is still open in a reader, then "" once every clip and the record have landed in `folder`, or
    what went wrong, with no part file left behind; `cancel()` stops it and leaves the folder as it
    was, and one still running when the interpreter exits is cancelled. `progress()` is (frames
    written, the video's frames as its container counts them, seconds since the start). ValueError
    when two shapes would write one file or there is nothing to cut."""

    def __init__(self, video, found, plate, quality):
        self.video, self.plate, self.quality = str(video), list(plate), str(quality)
        self.found = list(found)
        files = [file_for(name) for name, _ in self.found]
        if not files:
            raise ValueError("no shapes; wire a file selector into geometry")
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
        _running.add(self)

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

    def _say(self, said):
        self.said = said
        _running.discard(self)
        return said

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
                return self._say(f"ffmpeg exited {code}: {said}")
        try:
            self._land()
        except OSError as e:
            if time.perf_counter() - self.exited < LAND_PATIENCE:
                return None
            self._clear()
            return self._say(f"the clips did not land: {e}")
        return self._say("")

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
                       "crops": [{"name": name, "file": file_for(name), "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                                  "bytes": os.path.getsize(os.path.join(self.folder, file_for(name)))}
                                 for name, (y0, y1, x0, x1) in self.found]}, f, indent=1)
        if os.path.exists(self.report):
            os.remove(self.report)

    def cancel(self):
        if self.said is not None:
            return
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        if not self.log.closed:
            self.log.close()
        self._clear()
        self._say("cancelled")
