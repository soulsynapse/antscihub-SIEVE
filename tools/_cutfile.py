"""The files a cutting tool writes of a video into the player's store: how one is named, the one
ffmpeg run that writes them, how one lands, and which of a footage's nothing uses. Not a tool; a
tool imports it and no other tool (tests/test_seams.py).

`<store>/<footage print>/<label>-<key>.mp4` is a cut file of a video, the store being
sieve_player/store.py's, and the cut files of that file lie in `<key>/` beside it, to any depth, so
what was cut of a file is under it and goes with it. Its key is a digest of the footage's print, the
extent, which part of the footage it holds, and the recipe, how it was encoded, so a file is found
by its key and never written over: another rect, quality or footage is another file. The label is a
word for whoever reads the folder and names nothing. `<file>.json` beside it says what the file
holds and its size in bytes.
"""
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import weakref

import cv2

from sieve_player import store
from sieve_player.decoder import footage_print_by_stamp as footage_of

QUALITIES = ("lossless", "standard")
_X264 = ("-c:v", "libx264", "-preset", "medium", "-fps_mode", "passthrough", "-an")
ENCODE = {"lossless": (*_X264, "-qp", "0"), "standard": (*_X264, "-crf", "18")}    # in the key: other arguments are other files
PART, SIDECAR = store.PART, ".json"
KEYED = re.compile(r"-([0-9a-f]{16})\.mp4$")
LABEL_LEN = 40
SAID_LINES = 5      # how much of ffmpeg's stderr a failure carries


def _same(path):
    return os.path.normcase(os.path.abspath(path))


def _under(path):
    """The folder the cut files of the cut file at `path` lie in, or None for a path that is no cut file's."""
    m = KEYED.search(os.path.basename(path))
    return None if m is None else os.path.join(os.path.dirname(os.path.abspath(path)), m[1])


def folder_for(video, footage):
    """Where the cut files of `video`, whose print is `footage`, lie in the store as it is now:
    under a cut file of the store, the folder beside it named by its key; for any other video, the
    store's folder named by the print, wherever the video lies."""
    if _under(video) is not None and _same(video).startswith(_same(store.folder()) + os.sep):
        return _under(video)
    return os.path.join(store.folder(), footage)


def rect_extent(rect):
    """The extent of a cut to `rect`, (y0, y1, x0, x1) on the footage, at every row."""
    return {"kind": "rect", "rect": [int(v) for v in rect]}


def recipe(quality):
    return {"quality": quality, "encode": list(ENCODE[quality])}


def key(footage, extent, recipe):
    """The key of the cut file holding `extent` of the footage whose print is `footage`, encoded by
    `recipe`: the same however the members of either are ordered. ValueError for an extent that
    does not say its kind; nothing else of it is read."""
    if not isinstance(extent, dict) or not isinstance(extent.get("kind"), str):
        raise ValueError(f"an extent says its kind; got {extent!r}")
    said = json.dumps([footage, extent, recipe], sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(said.encode()).hexdigest()[:16]


def rect_key(footage, rect, quality):
    return key(footage, rect_extent(rect), recipe(quality))


def file_for(label, key):
    word = re.sub(r"[^\w.-]", "_", label)[:LABEL_LEN]
    return f"{word}-{key}.mp4"


def landed(folder):
    """key -> the cut file of that key in `folder`, read off the names now; empty with no folder."""
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return {}
    out = {}
    for name in names:
        if (m := KEYED.search(name)) is not None:
            out.setdefault(m[1], os.path.join(folder, name))
    return out


def sidecar(path):
    """What the sidecar beside the cut file at `path` says, or None with none there or one that does not read."""
    try:
        with open(path + SIDECAR, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def whole(path):
    """Whether the cut file at `path` is the size its sidecar says; one with no sidecar is taken as whole."""
    said = sidecar(path)
    return said is None or "bytes" not in said or said["bytes"] == os.path.getsize(path)


def unused(folder, in_use):
    """[(path, label, bytes)] of every clip in `folder` that is none of `in_use`, the bytes its own
    and those of everything cut of it."""
    held = {_same(p) for p in in_use}
    try:
        names = sorted(n for n in os.listdir(folder) if n.endswith(".mp4"))
    except OSError:
        return []
    out = []
    for name in names:
        path = os.path.join(folder, name)
        if _same(path) not in held:
            below = store.held(_under(path))[0] if _under(path) else 0
            out.append((path, (sidecar(path) or {}).get("label", os.path.splitext(name)[0]), os.path.getsize(path) + below))
    return out


def delete(paths):
    """Removes each clip of `paths`, its sidecar and everything cut of it. Answers [(path, why)]
    for each clip still there, or with something cut of it still there, one a reader has open
    among them."""
    kept = []
    for path in paths:
        try:
            os.remove(path)
            if os.path.exists(path + SIDECAR):
                os.remove(path + SIDECAR)
            if _under(path) and os.path.isdir(_under(path)):
                shutil.rmtree(_under(path))
        except OSError as e:
            kept.append((path, e.strerror or str(e)))
    return kept


def command(video, pieces, quality=QUALITIES[1], progress=None):
    """ffmpeg's command line cutting `video` once into the file `part` for each (part, rect) of
    `pieces`, its progress report written to the file `progress` when one is named."""
    argv = [shutil.which("ffmpeg") or "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            *(["-progress", progress] if progress else []), "-i", str(video)]
    for part, (y0, y1, x0, x1) in pieces:
        argv += ["-map", "0:v:0", "-vf", f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}:exact=1", *ENCODE[quality], "-f", "mp4", part]
    return argv


_running = weakref.WeakSet()    # the Cuts whose ffmpeg may still run: one the player leaves behind is stopped as it exits


@atexit.register
def _stop_running():
    for cut in list(_running):
        cut.cancel()


class Cut:
    """One ffmpeg run cutting `video` into a cut file for each (label, rect) of `found` whose key
    has none in the folder yet, rects as (y0, y1, x0, x1), at `quality`; `todo` is those it writes.
    `poll()` is None while it runs, then "" once each has landed with its sidecar, or what went
    wrong. No path that was there when it began is written, replaced or removed by it, however it
    ends, and it leaves no part file; a key another writer landed meanwhile keeps that writer's
    file. `cancel()` stops it, and one still running when the interpreter exits is cancelled.
    `progress()` is (frames written, the video's frames as its container counts them, seconds since
    the start). ValueError with no shapes, or with every one's file landed already."""

    def __init__(self, video, found, quality):
        self.video, self.quality = str(video), str(quality)
        if not found:
            raise ValueError("no shapes; wire a file selector into geometry")
        self.footage = footage_of(self.video)
        self.folder = folder_for(self.video, self.footage)
        have, self.todo = landed(self.folder), []      # todo: (label, rect, key)
        for label, rect in found:
            k = rect_key(self.footage, rect, self.quality)
            if k not in have and all(k != t[2] for t in self.todo):
                self.todo.append((label, tuple(rect), k))
        if not self.todo:
            raise ValueError(f"nothing to cut: every shape's clip is here at {self.quality}")
        os.makedirs(self.folder, exist_ok=True)
        self.parts = []
        for _ in self.todo:
            fd, part = tempfile.mkstemp(suffix=PART, dir=self.folder)
            os.close(fd)
            self.parts.append(part)
        cap = cv2.VideoCapture(self.video)
        self.total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        self.log = tempfile.TemporaryFile()
        fd, self.report = tempfile.mkstemp(suffix=".progress")
        os.close(fd)
        self.t0, self.done = time.perf_counter(), 0
        pieces = [(part, rect) for part, (_, rect, _) in zip(self.parts, self.todo)]
        self.proc = subprocess.Popen(command(self.video, pieces, self.quality, self.report),
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=self.log)
        self.said = None
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

    def _clear(self):
        for p in (*self.parts, *(p + SIDECAR for p in self.parts), self.report):
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
        self.log.seek(0)
        said = " | ".join(self.log.read().decode(errors="replace").strip().splitlines()[-SAID_LINES:])
        self.log.close()
        try:
            if code == 0:
                self._land()
        except OSError as e:
            code, said = None, str(e)
        self._clear()
        return self._say("" if code == 0 else f"ffmpeg exited {code}: {said}" if code else f"the clips did not land: {said}")

    def _land(self):
        for part, (label, rect, k) in zip(self.parts, self.todo):
            if k in landed(self.folder):
                continue
            final = os.path.join(self.folder, file_for(label, k))
            with open(part + SIDECAR, "w", encoding="utf-8", newline="\n") as f:
                json.dump({"video": os.path.basename(self.video), "footage": self.footage, "extent": rect_extent(rect),
                           "recipe": recipe(self.quality), "label": label, "bytes": os.path.getsize(part)}, f, indent=1)
            os.replace(part + SIDECAR, final + SIDECAR)     # whole before the clip has its name; one left by a clip since removed goes
            os.rename(part, final)

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
