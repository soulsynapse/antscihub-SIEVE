"""libav decoder, by PyAV, with two cursors on one file: the walk's, which only ever steps, and the
scrub's, which takes the display's jumps so they never land on the walk's. A sequential read steps
the cursor in use; a short jump ahead reads through, since a seek decodes from the last keyframe
anyway and costs what the decoder has measured it to cost here; anything else seeks. A seek lands
one row short and reads through it, because the tools that difference frames ask for row - 1 right
after row, and that second ask would otherwise be a second seek. A row is a frame's place among the
file's frames in the order they are shown: the frame a seek reads is numbered by where its own pts
lies among the pts of the file's packets, `frame_times`, never by a frame rate. On a file whose
packets do not give its frames' pts no seek is numbered and every row is stepped to from row 0."""
import hashlib
import os
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache

import av
import cv2
import numpy as np
from av.video.reformatter import VideoReformatter

LOOKBEHIND = 1          # rows a seek lands short of its target and reads through
SEEK_GUESS = 12.0       # steps a seek is taken to cost until one has been measured here
CLEAR = 16              # a store with nothing left but what its order keeps back clears a CLEARth of its limit, so the ranking is taken once for many discards
LUMA_FORMATS = {"yuv420p", "yuvj420p"}      # planar 8-bit 4:2:0: the first plane is the luma, rows x cols
_EXPAND = np.clip(np.round((np.arange(256) - 16) * 255 / 219), 0, 255).astype(np.uint8)   # limited-range luma to full
# BT.601 whatever the file says of itself, and yuv420p as limited range: the values cv2's FFmpeg plugin handed out,
# which every held result is of; docs/findings/2026-11-15-libav-asked-directly-against-the-plugin.md
_TO_BGR = {"format": "bgr24", "src_colorspace": "ITU601", "dst_colorspace": "ITU601", "src_color_range": "MPEG", "dst_color_range": "JPEG"}
_TURNS = {90: cv2.ROTATE_90_COUNTERCLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_CLOCKWISE}     # a frame's rotation, degrees -> the turn that shows it upright


def letting_go(held, rank, over, clear, least=0):
    """The keys of `held`, an OrderedDict least lately read first, that a store past its limit lets
    go of, each to be taken out of `held` by the caller before the next is asked for. `rank`
    answers None for a key that goes as any does and a rank for one kept back. While `over()`,
    those of None go, the least lately read first, each one kept back moved to the new end as it
    is met so that it is not met again until the store has turned over; with none of those left
    and the store still over, those kept back go, the highest rank first and the least lately read
    first of two alike, while `clear()`. `least` entries stay whatever. `rank` is asked of a key
    once at most, so nothing is ranked while a key of None is left."""
    kept = []
    for _ in range(len(held)):
        if not over() or len(held) <= least:
            return
        k = next(iter(held))
        r = rank(k)
        if r is None:
            yield k
        else:
            held.move_to_end(k)
            kept.append((r, k))
    if not over():
        return
    kept.sort(key=lambda rk: rk[0], reverse=True)
    for _, k in kept:
        if not clear() or len(held) <= least:
            return
        yield k


class EndOfStream(IndexError):
    """A read past the last row the stream has, which may be short of the container's claim. The
    only IndexError the worker closes a walk on; a tool's own IndexError is a failure."""


UNINDEXED = ("{name} has no index: a raw stream cannot be counted or seeked; remux it into a container first, "
             "ffmpeg -framerate FPS -i {name} -c copy {stem}.mp4")


def _open(path):
    """(container, its video stream) of the file at `path`; IOError when it will not open or has none."""
    try:
        container = av.open(path)
    except (av.error.FFmpegError, OSError) as exc:
        raise IOError(f"cannot open {path}") from exc
    if not container.streams.video:
        container.close()
        raise IOError(f"cannot open {path}")
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    return container, stream


def _first(frames):
    """(the first frame of `frames`, or None where there is none; the degrees it is to be shown turned by, of 0, 90, 180 and 270)."""
    try:
        frame = next(frames, None)
    except av.error.FFmpegError:
        frame = None
    return frame, 0 if frame is None else round(frame.rotation) % 360


def _facts(container, stream, path, turn=0):
    """(width, height, fps, count) of an open file whose frames are shown turned by `turn` degrees;
    IOError when its container claims no rows. The count is the container's own where it gives
    one, else its length at its frame rate."""
    fps = float(stream.average_rate or stream.guessed_rate or 0) or 30.0
    seconds = container.duration / 1e6 if container.duration else float((stream.duration or 0) * stream.time_base)
    n = stream.frames or int(seconds * fps + 0.5)
    if n <= 0:
        name = os.path.basename(str(path))
        raise IOError(UNINDEXED.format(name=name, stem=os.path.splitext(name)[0]))
    w, h = stream.codec_context.width, stream.codec_context.height
    return (h, w, fps, n) if turn in (90, 270) else (w, h, fps, n)


@lru_cache(maxsize=16)
def _probe(path, mtime):
    container, stream = _open(path)
    try:
        return _facts(container, stream, path, _first(_frames(container, stream))[1])
    finally:
        container.close()


def probe(src):
    """(width, height, fps, count), cached per path and mtime. The count is the container's claim,
    which the decoder corrects down when the stream ends short of it; a file whose container claims
    none, a raw stream, raises IOError, as the decoder does."""
    src = str(src)
    return _probe(src, os.stat(src).st_mtime)


STORE = None       # the window sets it: a function answering the store's folder, where frame_times keeps each file's; None keeps none
TIMES_DIR = "frame-times"   # the folder of the store they lie in, each `<footage print>.npy`
_times = {}        # path -> (the file's size and mtime when read, its frame times, whether this process read them off the packets)
_times_locks = {}  # path -> the lock on its reading: a seek waits on a reading of its own file begun ahead of it, and on no other file's
_times_guard = threading.Lock()


def _times_file(path):
    """Where the frame times of the file at `path` are kept, or None with no store set."""
    return None if STORE is None else os.path.join(STORE(), TIMES_DIR, f"{footage_print_by_stamp(path)}.npy")


def _kept_times(file):
    """The frame times `file` holds, or None with no such file or one that is not a table of them."""
    try:
        out = np.load(file, allow_pickle=False)
    except (OSError, ValueError, EOFError):
        return None
    return out if out.ndim == 2 and out.shape[1] == 3 and out.dtype == np.int64 and bool(np.all(np.diff(out[:, 0]) >= 0)) else None


def _keep_times(file, times):
    """Writes `times` at `file`, whole or not at all; a store that cannot be written keeps none."""
    part = None
    try:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        fd, part = tempfile.mkstemp(suffix=".tmp", dir=os.path.dirname(file))
        with os.fdopen(fd, "wb") as f:
            np.save(f, times)
        os.replace(part, file)
    except OSError:
        if part is not None and os.path.exists(part):
            os.remove(part)


def _packet_times(path):
    out = []
    try:
        container, stream = _open(path)
    except IOError:
        return np.zeros((0, 3), np.int64)
    try:
        for p in container.demux(stream):
            at = p.dts if p.pts is None else p.pts
            if at is not None and p.size and not p.is_discard:
                out.append((at, at if p.dts is None else p.dts, p.is_keyframe))
    except av.error.FFmpegError:
        pass
    finally:
        container.close()
    return np.array(sorted(out), np.int64).reshape(-1, 3)


def frame_times(path, anew=False):
    """A row for every frame of the video stream of `path`, in the order they are shown, so row r
    is row r's: its packet's pts, that packet's dts, and whether it is a keyframe, the first two in
    the stream's time base. Read off the packets with no frame decoded; a packet the container says
    to decode and not show has no row. The whole file is read for it, once: the table is kept in
    the store under the file's footage print where STORE is set, and in this process while the
    file's size and mtime stand. A kept table is taken on trust, the print telling two files as
    long apart by their first and last megabyte alone; `anew` is for whoever finds the file's
    frames disagree with it, and reads the packets unless this process already has, keeping what
    they give over what was kept. No rows where the file hands out no packets. Any thread; OSError
    with no file."""
    path = str(path)
    st = os.stat(path)
    stamp = st.st_size, st.st_mtime_ns
    with _times_guard:
        lock = _times_locks.setdefault(path, threading.Lock())
    with lock:
        held = _times.get(path, (None, None, False))
        if held[0] != stamp or (anew and not held[2]):
            file = _times_file(path)
            times = None if file is None or anew else _kept_times(file)
            read = times is None
            if read:
                times = _packet_times(path)
                if file is not None and len(times):
                    _keep_times(file, times)
                elif file is not None and os.path.exists(file):
                    os.remove(file)
            _times[path] = (stamp, times, read)
        return _times[path][1]


def read_frame_times_ahead(path):
    """Reads `frame_times(path)` on a thread of its own and does not wait, so a first seek finds
    the table read; a file that cannot be read is left for whoever reads it next to say."""
    def read():
        try:
            frame_times(path)
        except OSError:
            pass
    threading.Thread(target=read, name="frame-times", daemon=True).start()


class _TableRetaken(Exception):
    """The frame times a Decoder held were not its file's and it has taken them anew, every cursor
    reopened: the read under way is begun again."""


def _frames(container, stream):
    """The stream's frames in the order they are shown, from where the container stands; a packet that will not decode is passed over."""
    for packet in container.demux(stream):
        try:
            yield from packet.decode()
        except av.error.InvalidDataError:
            continue


class _Cursor:
    # pos: the row the next step reads; None once a step has failed, so the next read seeks.
    # counted: pos is a count of steps from row 0, where after a seek it is the landing's place among the frame times and the steps since
    # ahead: a frame taken off `frames` and not yet handed out, the next the cursor gives
    __slots__ = ("path", "container", "stream", "frames", "ahead", "to_bgr", "pos", "counted", "at")

    def __init__(self, path):
        self.path, self.container, self.to_bgr = path, None, VideoReformatter()
        self.reopen()

    def reopen(self):
        """A fresh container at row 0; IOError when the file will not open."""
        self.close()
        self.container, self.stream = _open(self.path)
        self.frames, self.ahead = _frames(self.container, self.stream), None
        self.pos, self.counted, self.at = 0, True, 0.0

    def seek(self, dts):
        self.container.seek(dts, stream=self.stream, backward=True)
        self.frames, self.ahead = _frames(self.container, self.stream), None

    def close(self):
        if self.container is not None:
            self.frames.close()
            self.container.close()
            self.container = None


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
    file's, by the function of that name, taken as it opens. `luma` is whether the stream's first
    plane is handed out as it is for the grays, and `limited` whether that plane is limited range."""

    def __init__(self, path, cache_bytes=4 << 30):
        self.path = str(path)
        self.footage_print = footage_print(self.path)
        walk = _Cursor(self.path)
        walk.ahead, turn = _first(walk.frames)
        self._turn = _TURNS.get(turn)           # how every frame is turned as it is handed out, the file's rotation being its first frame's
        try:
            self.width, self.height, self.fps, self.count = _facts(walk.container, walk.stream, self.path, turn)
        except IOError:
            walk.close()
            raise
        fmt = walk.stream.codec_context.pix_fmt
        self.luma = fmt in LUMA_FORMATS
        self.limited = self.luma and not fmt.startswith("yuvj")
        self._output = "bgr"
        self._cursors = {"walk": walk, "scrub": None}   # the scrub's opens on its first use
        self._use = "walk"
        self._cache = OrderedDict()
        self._cache_bytes, self._cache_limit = 0, cache_bytes
        self._cache_lock = threading.Lock()     # the dict only: a GUI peek never waits on a decode
        self._cap_lock = threading.Lock()       # the containers and the cursor in use
        self.decodes = self.seeks = 0           # frames handed out, those a seek decodes on its way to its row not among them
        self.reads = self.cache_hits = 0        # read() calls, and those the cache answered
        self.evictions = 0                      # frames the cache dropped for room
        self.step_ms = self.seek_ms = None      # running means of what a step and a seek cost on this file
        self.on_evict = None                    # (row, bytes) for each frame the cache drops, after the lock
        self.order = None                       # as Memo.order, of a row: unset, every frame goes the least lately read first
        self._times = None                      # frame_times of the file, taken before the first seek
        self._keys = None                       # the rows of its keyframes, ascending
        self._earliest_landing = 0              # the row a seek to the first keyframe read, once one has read past row 0
        self._counts_only = False               # the packets' pts do not give the frames': no seek is numbered on this file
        self._retaken = False                   # the frame times have been taken anew once; a second disagreement is the file's own

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
        """What read() hands out, before it is cached: "bgr"; "gray", full range; or "luma", the
        stream's own plane in the stream's range, 16 to 235 on most camera files. On an 8-bit 4:2:0
        stream both grays come from the plane with no colour conversion, gray through a lookup
        table when the stream is limited range; otherwise both are converted from BGR. Setting it
        empties the cache."""
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

    def _fits(self, f):
        # a frame of the other kind, decoded before a switch and landing after it, is not served
        return (f.ndim == 2) == (self._output != "bgr")

    def cached(self, row):
        """Cache-only read; never touches a container. Safe from the GUI thread."""
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
        """Takes hold at once: frames go, the least lately read first and those `order` keeps back
        last, until the cache is within it, one frame staying whatever the limit, and `on_evict`
        is told of each. Any thread."""
        with self._cache_lock:
            self._cache_limit = n
            gone = self._trim()
        self._tell(gone)

    def _trim(self):
        gone = []
        if self._cache_bytes > self._cache_limit and self.order is not None:
            for r in letting_go(self._cache, self.order(), lambda: self._cache_bytes > self._cache_limit,
                                lambda: self._cache_bytes > self._cache_limit - self._cache_limit // CLEAR, least=1):
                old = self._cache.pop(r)
                self._cache_bytes -= old.nbytes
                gone.append((r, old.nbytes))
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
            try:
                return self._read(row)
            except _TableRetaken:
                return self._read(row)

    def _read(self, row):
        cur = self._cursors[self._use]
        if cur is None:
            cur = self._cursors[self._use] = _Cursor(self.path)
        if self._counts_only and not cur.counted:
            cur.pos = None
        if cur.pos is None or row < cur.pos or (row - cur.pos > self._read_through() and not self._counts_only):
            if self._times is None:     # before the seek is timed: the reading is once a file, and no part of what a seek costs
                self._take_times(frame_times(self.path))
                if not len(self._times):
                    self._unnumbered("it hands out no packet")
            t = time.perf_counter()
            f = self._seek(cur, max(0, row - LOOKBEHIND))
            self.seeks += 1
            self.seek_ms = self._mean(self.seek_ms, (time.perf_counter() - t) * 1000, self.seeks)
        while cur.pos <= row:
            f = self._step(cur)
        return f

    def _take_times(self, times):
        self._times, self._keys = times, np.flatnonzero(times[:, 2])

    def _seek(self, cur, target):
        """Reads row `target` and returns its frame, the cursor left after it; or returns None with
        the cursor reopened at row 0, where no seek lands at or before it, which is learned of a
        file once, and on a file whose packets do not give its frames' pts. The container is asked
        for the dts of the last keyframe at or before the row, which is where a seek to a time
        lands on its first keyframe, a transport stream's too, and the frames from there are
        decoded and not handed out until the row's pts comes; a landing past the row is asked again
        a keyframe earlier. docs/findings/2026-11-15-libav-asked-directly-against-the-plugin.md."""
        if not self._counts_only and target >= len(self._times):
            self._doubt(f"row {target} is past the last of the frame times held")
            cur.pos = len(self._times)
            self._ended(cur)
        k = -1 if self._counts_only else int(np.searchsorted(self._keys, target, side="right")) - 1
        while k >= 0 and not self._counts_only and target >= self._earliest_landing:
            key = int(self._keys[k])
            cur.seek(int(self._times[key, 1]))
            frame = self._next(cur, ending=False)
            landed = None if frame is None else self._row_of(frame)
            if frame is not None and landed is None:
                self._unnumbered(f"the frame a seek to row {key} read has the pts of no packet")
                break
            if frame is None or landed > target:
                if k == 0 and frame is not None:
                    self._earliest_landing = landed
                k -= 1
                continue
            cur.counted = False
            while landed < target:
                cur.pos = landed + 1
                frame = self._next(cur)
                if self._row_of(frame) != cur.pos:
                    self._unnumbered(f"the frame after row {landed} has not the pts of row {cur.pos}'s packet")
                    frame = None
                    break
                landed += 1
            if frame is None:
                break
            cur.pos = target
            return self._hand(cur, frame)
        cur.reopen()
        return None

    def _row_of(self, frame):
        """The row `frame` is, by its pts' place among the frame times; None for a pts that is no packet's."""
        at = frame.dts if frame.pts is None else frame.pts
        if at is None:
            return None
        r = int(np.searchsorted(self._times[:, 0], at))
        return r if r < len(self._times) and self._times[r, 0] == at else None

    def _doubt(self, why):
        """Reads the frame times anew where the ones held were kept and not read off the packets
        here; where the packets give others, takes those, reopens every cursor, empties the cache,
        which may hold a row misnumbered, and raises _TableRetaken for `read` to begin again. Once
        a Decoder."""
        if self._retaken:
            return
        self._retaken = True
        fresh = frame_times(self.path, anew=True)
        if np.array_equal(fresh, self._times):
            return
        print(f"{os.path.basename(self.path)}: {why}: the frame times held were not this file's, "
              "and are read anew off its packets", file=sys.stderr)
        self._take_times(fresh)
        self._earliest_landing = 0
        for cur in self._cursors.values():
            if cur is not None:
                cur.reopen()
        self.empty()
        raise _TableRetaken

    def _unnumbered(self, why):
        """From here no seek is numbered on the file, unless `_doubt` finds the frame times held were not its own; said once, and the cache emptied."""
        self._doubt(why)
        self._counts_only = True
        print(f"{os.path.basename(self.path)}: {why}, so no seek is numbered on it and every row is stepped to from row 0",
              file=sys.stderr)
        self.empty()

    def _read_through(self):
        """Rows ahead of the cursor it is cheaper to step through than to seek over."""
        if self.step_ms and self.seek_ms:
            return self.seek_ms / self.step_ms
        return SEEK_GUESS

    def _next(self, cur, ending=True):
        """The cursor's next frame, not yet handed out. Where the stream gives none: None when not
        `ending`; else the stream has ended at the cursor's row, the count comes down to it where it
        claimed more, and EndOfStream is raised."""
        frame, cur.ahead = cur.ahead, None
        if frame is None:
            try:
                frame = next(cur.frames, None)
            except av.error.FFmpegError:
                frame = None
        if frame is not None:
            if frame.time is not None:
                cur.at = frame.time
            return frame
        if not ending:
            return None
        self._ended(cur)

    def _ended(self, cur):
        row, cur.pos = cur.pos, None
        if 0 <= row < self.count:
            # the only record of why, since dev/console.py hushes libav's; SIEVE_C_STDERR=1 shows it
            print(f"{os.path.basename(self.path)}: the stream ended at row {row} of the container's {self.count}, "
                  f"at {cur.at:.3f} s; the count is now {row}", file=sys.stderr)
            self.count = row
        raise EndOfStream(f"row {row} past end of {self.path}")

    def _step(self, cur):
        t = time.perf_counter()
        frame = self._next(cur)
        if self._times is not None and not self._counts_only and (timed := self._row_of(frame)) != cur.pos:
            self._unnumbered(f"the frame stepped to as row {cur.pos} has the pts of "
                             f"{'no packet' if timed is None else f'the packet of row {timed}'}")
            if not cur.counted:
                cur.reopen()
                return None
        f = self._hand(cur, frame)
        self.step_ms = self._mean(self.step_ms, (time.perf_counter() - t) * 1000, self.decodes)
        return f

    def _hand(self, cur, frame):
        """`frame` as the output in force, cached as the cursor's row, the cursor moved past it."""
        output = self._output
        if output != "bgr" and self.luma:
            p = frame.planes[0]
            f = np.frombuffer(p, np.uint8).reshape(p.height, p.line_size)[:, :p.width]
            f = cv2.LUT(f, _EXPAND) if output == "gray" and self.limited else f.copy()
        else:
            f = cur.to_bgr.reformat(frame, **_TO_BGR).to_ndarray()
            if output != "bgr":
                f = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if self._turn is not None:
            f = cv2.rotate(f, self._turn)
        f.setflags(write=False)     # the cache's frame is every reader's
        self.decodes += 1
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
                cur.close()
