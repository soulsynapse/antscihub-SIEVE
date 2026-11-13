"""cv2 BGR decoder with two cursors on one file: the walk's, which only ever steps, and the scrub's,
which takes the display's jumps so they never land on the walk's. A sequential read steps the cursor
in use; a short jump ahead reads through, since a seek decodes from the last keyframe anyway and
costs what the decoder has measured it to cost here; anything else seeks. A seek lands one row
short and reads through it, because the tools that difference frames ask for row - 1 right after
row, and that second ask would otherwise be a second seek. ahead() has a thread of the decoder's own
step the walk's cursor into the cache in front of a walk's reads, until rest()."""
import os
import sys
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache

import cv2
import numpy as np

LOOKBEHIND = 1          # rows a seek lands short of its target and reads through
AHEAD_ROWS = 64         # the most rows the reading thread keeps decoded past the last one read in step
AHEAD_SWITCH_S = 0.0005 # the interpreter's switch interval while a thread reads ahead: at Python's 5 ms it waits on the tools between frames
SEEK_GUESS = 12.0       # steps a seek is taken to cost until one has been measured here
LUMA_FORMATS = {b"I420"}    # planar 8-bit 4:2:0: unconverted, cv2 hands out the luma plane as rows x cols
QUIET = False   # play() sets it once C-level stderr goes nowhere; the plugin warns on every unconverted frame otherwise
_QUIET_LEVELS = {"OFF", "DISABLED", "SILENT", "FATAL", "ERROR", "0", "1", "2"}
_EXPAND = np.clip(np.round((np.arange(256) - 16) * 255 / 219), 0, 255).astype(np.uint8)   # limited-range luma to full


class EndOfStream(IndexError):
    """A read past the last row the stream has, which may be short of the container's claim. The
    only IndexError the worker closes a walk on; a tool's own IndexError is a failure."""


def _quiet():
    return QUIET or os.environ.get("OPENCV_LOG_LEVEL", "").upper() in _QUIET_LEVELS


def _luma_range(path):
    """(usable, limited) for the luma plane of row 0: usable when it is the shape of the converted
    frame, limited when cv2's own conversion, which knows the stream's range, sits at a slope near
    219/255 above it. A flat row that cannot tell is taken as limited, the camera norm."""
    raw, rgb = cv2.VideoCapture(path, cv2.CAP_FFMPEG), cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    try:
        raw.set(cv2.CAP_PROP_CONVERT_RGB, 0)
        ok, y = raw.read()
        ok2, bgr = rgb.read()
    finally:
        raw.release()
        rgb.release()
    if not (ok and ok2) or y.ndim != 2 or y.shape != bgr.shape[:2]:
        return False, False
    y = y.ravel()[::97].astype(np.float64)
    g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).ravel()[::97].astype(np.float64)
    var = y.var()
    if var < 25.0:
        return True, True
    slope = ((y - y.mean()) * (g - g.mean())).mean() / var
    return True, slope > 1.08


UNINDEXED = ("{name} has no index: a raw stream cannot be counted or seeked; remux it into a container first, "
             "ffmpeg -framerate FPS -i {name} -c copy {stem}.mp4")


def _facts(cap, path):
    """(width, height, fps, count) of an open capture; IOError when its container claims no rows."""
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if n <= 0:
        name = os.path.basename(str(path))
        raise IOError(UNINDEXED.format(name=name, stem=os.path.splitext(name)[0]))
    return int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), cap.get(cv2.CAP_PROP_FPS) or 30.0, n


@lru_cache(maxsize=16)
def _probe(path, mtime):
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            raise IOError(f"cannot open {path}")
        return _facts(cap, path)
    finally:
        cap.release()


def probe(src):
    """(width, height, fps, count) via cv2, cached per path and mtime. The count is the container's
    claim, which the decoder corrects down when the stream ends short of it; a file whose container
    claims none, a raw stream, raises IOError, as the decoder does."""
    src = str(src)
    return _probe(src, os.stat(src).st_mtime)


class _Cursor:
    __slots__ = ("cap", "pos", "path", "luma")      # pos: the row the next step reads; None once a step has failed, so the next read seeks

    def __init__(self, path, luma):
        self.path, self.luma, self.cap = path, luma, None
        self.reopen()

    def reopen(self, luma=None):
        """A fresh capture at row 0, the luma plane's or BGR's: the only way to change what it decodes
        to, since the plugin garbles every frame after CAP_PROP_CONVERT_RGB is flipped on a capture
        that has read one."""
        if self.cap is not None:
            self.cap.release()
        if luma is not None:
            self.luma = luma
        self.cap = cv2.VideoCapture(self.path, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_CONVERT_RGB, 0 if self.luma else 1)
        self.pos = 0


class _Ahead:
    """One run of the reading thread over rows [start, end): `front` is the last row read() was asked
    in step, `next` the row the thread decodes next, never more than `lead` past `front`."""

    def __init__(self, start, end, lead):
        self.start, self.end, self.lead = start, end, lead
        self.front = self.last = -2
        self.next = start
        self.stop = self.waiting = False
        self.cv = threading.Condition()
        self.thread = None

    def saw(self, row):
        if (row == self.last + 1 or row == self.front + 1) and self.start <= row < self.end:
            self.front = row
            if self.waiting:
                with self.cv:
                    self.cv.notify()
        self.last = row


class Decoder:
    """Opens an indexed container; a file that will not open, or whose container claims no rows (a
    raw stream, which cannot be seeked), raises IOError saying which."""

    def __init__(self, path, cache_bytes=4 << 30):
        self.path = str(path)
        walk = _Cursor(self.path, luma=False)
        if not walk.cap.isOpened():
            raise IOError(f"cannot open {path}")
        cap = walk.cap
        try:
            self.width, self.height, self.fps, self.count = _facts(cap, self.path)
        except IOError:
            cap.release()
            raise
        fmt = int(cap.get(cv2.CAP_PROP_CODEC_PIXEL_FORMAT)).to_bytes(4, "little", signed=True)
        self.luma = fmt in LUMA_FORMATS and _quiet()
        self._limited = None    # measured at the first gray read, two decodes of row 0
        self._output = "bgr"
        self._cursors = {"walk": walk, "scrub": None}   # the scrub's opens on its first use
        self._use = "walk"
        self._cache = OrderedDict()
        self._cache_bytes, self._cache_limit = 0, cache_bytes
        self._cache_lock = threading.Lock()     # the dict only: a GUI peek never waits on a decode
        self._cap_lock = threading.Lock()       # the captures and the cursor in use
        self.decodes = self.seeks = 0
        self.reads = self.cache_hits = 0        # read() calls, and those the cache answered
        self.evictions = 0                      # frames the cache dropped for room
        self.step_ms = self.seek_ms = None      # running means of what a step and a seek cost on this file
        self.on_evict = None                    # (row, bytes) for each frame the cache drops, after the lock
        self._inexact_said = False
        self._ahead = None                      # the _Ahead running, if one is
        self._fresh = set()                     # rows the reading thread decoded that no read() has taken yet
        self._dropped = []                      # (row, bytes) the reading thread's puts evicted, told to on_evict by the next read()
        self.ahead_decodes = self.ahead_seeks = 0   # the reading thread's, counted in `decodes` only as a read() takes each row
        self._interval = None

    @contextmanager
    def scrub(self):
        """Reads inside run on the scrub cursor; the walk's stays where the walk left it."""
        with self._cap_lock:
            self._use = "scrub"
        try:
            yield
        finally:
            with self._cap_lock:
                self._use = "walk"

    @property
    def output(self):
        """What read() hands out, before it is cached: "bgr" as decoded; "gray", full range; or
        "luma", the decoder's own plane in the stream's range, 16 to 235 on most camera files. On an
        8-bit 4:2:0 stream with QUIET set both grays come from the plane and skip the YUV-to-BGR
        conversion, gray through a lookup table when the stream is limited range; otherwise both are
        converted from BGR. Setting it empties the cache."""
        return self._output

    @output.setter
    def output(self, value):
        if value not in ("bgr", "gray", "luma"):
            raise ValueError(f"decoder output {value!r}; one of bgr, gray, luma")
        with self._cache_lock:
            if value == self._output:
                return
            self._output, self._cache_bytes = value, 0
            self._cache.clear()

    @property
    def limited(self):
        """Whether the luma plane is limited range, measured on row 0 the first time it is asked."""
        if self._limited is None:
            self.luma, self._limited = _luma_range(self.path) if self.luma else (False, False)
        return self._limited

    def _luma_read(self):
        return self.luma and self._output != "bgr"

    def _fits(self, f):
        # a frame of the other kind, decoded before a switch and landing after it, is not served
        return (f.ndim == 2) == (self._output != "bgr")

    def cached(self, row):
        """Cache-only read; never touches a capture. Safe from the GUI thread."""
        with self._cache_lock:
            f = self._cache.get(row)
            return f if f is None or self._fits(f) else None

    def empty(self):
        """Drops every cached frame and tells `on_evict` of none. Any thread."""
        with self._cache_lock:
            self._cache.clear()
            self._cache_bytes = 0

    @property
    def cache_bytes(self):
        return self._cache_bytes

    @property
    def cache_limit(self):
        return self._cache_limit

    def read(self, row) -> np.ndarray:
        """The frame at `row`. A row the reading thread decoded counts as a decode of this read, the
        first to take it, and not as a cache hit, though the time was the other thread's."""
        self.reads += 1
        a = self._ahead
        if a is not None and self._use == "walk":
            a.saw(row)
        if self._dropped:
            dropped, self._dropped = self._dropped, []
            if self.on_evict is not None:
                for r, n in dropped:
                    self.on_evict(r, n)
        f = self.cached(row)
        held = f is not None
        if not held:
            f = self._fetch(row, self._use)
        if row in self._fresh:
            self._fresh.discard(row)
            self.decodes += 1
        elif held:
            self.cache_hits += 1
        return f

    def _fetch(self, row, use, ahead=False):
        with self._cap_lock:
            f = self.cached(row)    # the other thread may have decoded it while this one waited on the lock
            if f is not None:
                return f
            cur = self._cursors[use]
            if cur is None:
                cur = self._cursors[use] = _Cursor(self.path, self._luma_read())
            if cur.luma != self._luma_read():
                cur.reopen(self._luma_read())   # here, under the lock a read holds, never from the setter
            if cur.pos is None or not 0 <= row - cur.pos <= self._read_through():
                t = time.perf_counter()
                self._seek(cur, max(0, row - LOOKBEHIND))
                f = self._step(cur, ahead)
                if ahead:
                    self.ahead_seeks += 1
                else:
                    self.seeks += 1
                self.seek_ms = self._mean(self.seek_ms, (time.perf_counter() - t) * 1000, self.seeks + self.ahead_seeks)
            while cur.pos <= row:
                f = self._step(cur, ahead)
        return f

    def ahead(self, start, end):
        """Starts a thread decoding rows of [start, end) on the walk's cursor into the cache, up to
        AHEAD_ROWS past the last row read() was asked in step and never so far that the cache drops a
        row not yet read; it decodes nothing until two reads come in step. Replaces one already
        running; a cache too small to hold three frames starts none. The interpreter's switch interval
        is AHEAD_SWITCH_S until rest(). The thread that calls read()."""
        self.rest()
        frame = self.width * self.height * (3 if self._output == "bgr" else 1)
        lead = min(AHEAD_ROWS, self._cache_limit // frame - 2)
        if lead < 1 or end - start < 2:
            return
        a = self._ahead = _Ahead(start, end, lead)
        self._interval = sys.getswitchinterval()
        sys.setswitchinterval(AHEAD_SWITCH_S)
        a.thread = threading.Thread(target=self._read_ahead, args=(a,), name="decode", daemon=True)
        a.thread.start()

    def rest(self):
        """Stops the reading thread, if one runs, and puts the switch interval back. The thread that calls read()."""
        a, self._ahead = self._ahead, None
        if a is None:
            return
        with a.cv:
            a.stop = True
            a.cv.notify()
        a.thread.join()
        self._fresh.clear()
        sys.setswitchinterval(self._interval)

    def _read_ahead(self, a):
        while True:
            with a.cv:
                while not a.stop:
                    front = a.front
                    if not front < a.next <= front + a.lead + 1:
                        a.next = front + 1
                    if front >= a.start and a.next <= min(front + a.lead, a.end - 1):
                        break
                    a.waiting = True
                    a.cv.wait()
                a.waiting = False
                if a.stop:
                    return
            try:
                if self.cached(a.next) is None:
                    self._fetch(a.next, "walk", ahead=True)
            except Exception:
                return      # the read() that comes to this row meets the same and answers for it
            a.next += 1

    def _seek(self, cur, target):
        """Puts the cursor at or before `target`, where the plugin reports it landed: a container that
        seeks inexactly lands on a keyframe near the target, so the landing is read back, a landing past
        the target is retried further back, and the rows between are stepped through by read()."""
        back = 0
        while True:
            cur.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target - back))
            landed = int(cur.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if landed < 0:
                cur.pos = max(0, target - back)
                return
            if landed != target and not self._inexact_said:
                self._inexact_said = True
                print(f"{os.path.basename(self.path)}: a seek to row {target} landed on {landed}; the container seeks "
                      "inexactly, so rows are stepped through from where each seek lands", file=sys.stderr)
            if landed <= target or target - back == 0:
                cur.pos = landed
                return
            back = 2 * (back or landed - target)

    def _read_through(self):
        """Rows ahead of the cursor it is cheaper to step through than to seek over."""
        if self.step_ms and self.seek_ms:
            return self.seek_ms / self.step_ms
        return SEEK_GUESS

    def _step(self, cur, ahead=False):
        t = time.perf_counter()
        ok, f = cur.cap.read()
        if ahead:
            self.ahead_decodes += 1
        else:
            self.decodes += 1
        if not ok:
            row, cur.pos = cur.pos, None
            if 0 <= row < self.count:
                # the only record of why, since dev/console.py hushes libav's; SIEVE_C_STDERR=1 shows it
                print(f"{os.path.basename(self.path)}: the stream ended at row {row} of the container's {self.count}, "
                      f"at {cur.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000:.3f} s; the count is now {row}", file=sys.stderr)
                self.count = row
            raise EndOfStream(f"row {row} past end of {self.path}")
        self.step_ms = self._mean(self.step_ms, (time.perf_counter() - t) * 1000, self.decodes + self.ahead_decodes)
        if self._output != "bgr" and f.ndim == 3:
            f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        elif self._output == "gray" and self.limited:
            f = cv2.LUT(f, _EXPAND)
        self._put(cur.pos, f, ahead)
        cur.pos += 1
        return f

    @staticmethod
    def _mean(mean, x, n):
        return x if mean is None else mean + (x - mean) / min(n, 64)

    def _put(self, row, bgr, ahead=False):
        gone = []
        with self._cache_lock:
            if not self._fits(bgr):
                return
            if row in self._cache:
                self._cache.move_to_end(row)
                return
            self._cache[row] = bgr
            if ahead:
                self._fresh.add(row)     # under the lock cached() takes, so no read sees the frame without it
            self._cache_bytes += bgr.nbytes
            while self._cache_bytes > self._cache_limit and len(self._cache) > 1:
                r, old = self._cache.popitem(last=False)
                self._cache_bytes -= old.nbytes
                gone.append((r, old.nbytes))
            self.evictions += len(gone)
        if ahead:
            self._dropped.extend(gone)
        elif self.on_evict is not None:
            for r, n in gone:
                self.on_evict(r, n)

    def close(self):
        self.rest()
        for cur in self._cursors.values():
            if cur is not None:
                cur.cap.release()
