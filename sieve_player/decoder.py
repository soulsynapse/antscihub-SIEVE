"""cv2 BGR decoder with two cursors on one file: the walk's, which only ever steps, and the scrub's,
which takes the display's jumps so they never land on the walk's. A sequential read steps the cursor
in use; a short jump ahead reads through, since a seek decodes from the last keyframe anyway and
costs what the decoder has measured it to cost here; anything else seeks. A seek lands one row
short and reads through it, because the tools that difference frames ask for row - 1 right after
row, and that second ask would otherwise be a second seek. The frame a seek reads is numbered by its
own time, never by where the plugin says the seek landed; on a file where a stepped frame's time
gives another row than the count, a varying rate or frames missing, no seek is numbered and every
row is stepped to from row 0."""
import hashlib
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


def _first_ms(path):
    """CAP_PROP_POS_MSEC after row 0 is read on a capture of its own; 0.0 where nothing reads."""
    cap = cv2.VideoCapture(path, cv2.CAP_FFMPEG)
    try:
        return cap.get(cv2.CAP_PROP_POS_MSEC) if cap.read()[0] else 0.0
    finally:
        cap.release()


class _Cursor:
    # pos: the row the next step reads; None once a step has failed, so the next read seeks.
    # counted: pos is a count of steps from row 0, where after a seek it is the landing's time and the steps since
    __slots__ = ("cap", "pos", "path", "luma", "counted")

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
        self.pos, self.counted = 0, True


SLICE = 1 << 20     # the bytes of a file's head, and of its tail, that footage_print reads


def footage_print(path):
    """Which footage the file at `path` is, the same wherever it lies and however its path is
    spelled: a digest of its size, its first SLICE bytes and its last, so two files as long that
    differ only between those are one. Of a `path` that is no file, the digest of the path."""
    path = str(path)
    if not os.path.isfile(path):
        return hashlib.sha1(path.encode()).hexdigest()[:16]
    size = os.path.getsize(path)
    h = hashlib.sha1(str(size).encode())
    with open(path, "rb") as f:
        h.update(f.read(SLICE))
        if size > SLICE:
            f.seek(max(SLICE, size - SLICE))
            h.update(f.read(SLICE))
    return h.hexdigest()[:16]


_prints = {}        # path -> (the file's size and mtime when read, its footage print)


def footage_print_by_stamp(path):
    """`footage_print` of the file at `path`, read again only when its size or mtime moved; OSError with no file."""
    path = str(path)
    st = os.stat(path)
    stamp = st.st_size, st.st_mtime_ns
    if _prints.get(path, (None,))[0] != stamp:
        _prints[path] = (stamp, footage_print(path))
    return _prints[path][1]


class Decoder:
    """Opens an indexed container; a file that will not open, or whose container claims no rows (a
    raw stream, which cannot be seeked), raises IOError saying which. `footage_print` is the
    file's, by the function of that name, taken as it opens."""

    def __init__(self, path, cache_bytes=4 << 30):
        self.path = str(path)
        self.footage_print = footage_print(self.path)
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
        self._first_ms = None                   # row 0's time, read at the first seek
        self._earliest_landing = 0              # the row a seek to row 0 read, once one has read past row 0
        self._counts_only = False               # a stepped frame's time gave another row than the count: no seek is numbered on this file

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

    @cache_limit.setter
    def cache_limit(self, n):
        """Takes hold at once: the frames least lately read go until the cache is within it, one
        frame staying whatever the limit, and `on_evict` is told of each. Any thread."""
        with self._cache_lock:
            self._cache_limit = n
            gone = self._trim()
        self._tell(gone)

    def _trim(self):
        gone = []
        while self._cache_bytes > self._cache_limit and len(self._cache) > 1:
            r, old = self._cache.popitem(last=False)
            self._cache_bytes -= old.nbytes
            gone.append((r, old.nbytes))
        self.evictions += len(gone)
        return gone

    def _tell(self, gone):
        if self.on_evict is not None:
            for r, n in gone:
                self.on_evict(r, n)

    def ends_at(self, row):
        """The stream is known to end at `row`, by a reader of another file of this footage or
        another process's of this one: the count comes down to it, and never goes up."""
        self.count = min(self.count, row)

    def read(self, row) -> np.ndarray:
        self.reads += 1
        f = self.cached(row)
        if f is not None:
            self.cache_hits += 1
            return f
        with self._cap_lock:
            cur = self._cursors[self._use]
            if cur is None:
                cur = self._cursors[self._use] = _Cursor(self.path, self._luma_read())
            if cur.luma != self._luma_read():
                cur.reopen(self._luma_read())   # here, under the lock a read holds, never from the setter
            if self._counts_only and not cur.counted:
                cur.pos = None
            if cur.pos is None or row < cur.pos or (row - cur.pos > self._read_through() and not self._counts_only):
                t = time.perf_counter()
                f = self._seek(cur, max(0, row - LOOKBEHIND))
                self.seeks += 1
                self.seek_ms = self._mean(self.seek_ms, (time.perf_counter() - t) * 1000, self.seeks)
            while cur.pos <= row:
                f = self._step(cur)
        return f

    def _seek(self, cur, target):
        """Reads a row at or before `target` and returns its frame, the cursor left after it; or
        returns None with the cursor reopened at row 0, where no seek lands that early, which is
        learned of a file once, and on a file whose times do not count its rows. A landing past the
        target is asked again further back. The row is
        the one the frame's own time gives: the plugin does not check where a seek to row 0 or 1
        landed, and of a target it could not get behind it says the row before the one it reads
        next; docs/findings/2026-11-15-why-no-seek-lands-in-the-mts-first-thirty-rows.md."""
        back = 0
        while not self._counts_only and target >= self._earliest_landing:
            ask = max(0, target - back)
            cur.cap.set(cv2.CAP_PROP_POS_FRAMES, ask)
            cur.pos = ask       # the row an end of stream at this read is said of
            f = self._step(cur, landing=True)
            cur.counted = False
            landed = cur.pos - 1
            if landed != ask and not self._inexact_said:
                self._inexact_said = True
                print(f"{os.path.basename(self.path)}: a seek to row {ask} read row {landed}; the container seeks "
                      "inexactly, so rows are stepped through from where each seek lands", file=sys.stderr)
            if landed <= target:
                return f
            if ask == 0:
                self._earliest_landing = landed
            back = 2 * (back or landed - target)
        cur.reopen()
        return None

    def _row_read(self, cur):
        """The row the cursor's last read handed out, by the frame's time against row 0's."""
        if self._first_ms is None:
            self._first_ms = _first_ms(self.path)
        return int((cur.cap.get(cv2.CAP_PROP_POS_MSEC) - self._first_ms) * self.fps / 1000 + 0.5)

    def _read_through(self):
        """Rows ahead of the cursor it is cheaper to step through than to seek over."""
        if self.step_ms and self.seek_ms:
            return self.seek_ms / self.step_ms
        return SEEK_GUESS

    def _step(self, cur, landing=False):
        t = time.perf_counter()
        ok, f = cur.cap.read()
        self.decodes += 1
        if ok and landing:
            cur.pos = self._row_read(cur)
        elif ok and not self._counts_only and (timed := self._row_read(cur)) != cur.pos:
            self._counts_only = True
            print(f"{os.path.basename(self.path)}: the frame stepped to as row {cur.pos} is timed as row {timed}; the file's "
                  "frame rate varies or frames are missing, so no seek is numbered on it and every row is stepped to "
                  "from row 0", file=sys.stderr)
            self.empty()        # a row a seek read before this may be cached under another row's number
            if not cur.counted:
                cur.reopen()
                return None
        if not ok:
            row, cur.pos = cur.pos, None
            if 0 <= row < self.count:
                # the only record of why, since dev/console.py hushes libav's; SIEVE_C_STDERR=1 shows it
                print(f"{os.path.basename(self.path)}: the stream ended at row {row} of the container's {self.count}, "
                      f"at {cur.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000:.3f} s; the count is now {row}", file=sys.stderr)
                self.count = row
            raise EndOfStream(f"row {row} past end of {self.path}")
        self.step_ms = self._mean(self.step_ms, (time.perf_counter() - t) * 1000, self.decodes)
        if self._output != "bgr" and f.ndim == 3:
            f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        elif self._output == "gray" and self.limited:
            f = cv2.LUT(f, _EXPAND)
        self._put(cur.pos, f)
        cur.pos += 1
        return f

    @staticmethod
    def _mean(mean, x, n):
        return x if mean is None else mean + (x - mean) / min(n, 64)

    def _put(self, row, bgr):
        with self._cache_lock:
            if not self._fits(bgr):
                return
            if row in self._cache:
                self._cache.move_to_end(row)
                return
            self._cache[row] = bgr
            self._cache_bytes += bgr.nbytes
            gone = self._trim()
        self._tell(gone)

    def close(self):
        for cur in self._cursors.values():
            if cur is not None:
                cur.cap.release()
