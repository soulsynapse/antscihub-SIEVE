"""Feel the session plan: hunt the full timeline, land a window, tune, jump.

The storage explorer feels the *tier stack* on one region; this feels the
*plan* — the shape a real SIEVE session takes once the cut is demoted from
prerequisite to write-behind:

  hunt        one slider over the whole file — click anywhere to jump.
              Outside any window, requests route to the display proxy
              (5-9 ms drags) or kf-snap on the original (~130 ms, and every
              full frame decoded on that route gets its crop sliced out and
              admitted to RAM for free — bytes that already exist are never
              refused). The crop is drawn, not configured: drag a rectangle
              on the full-frame view; a new crop is a form change and wipes
              RAM and chunks, because a stored small frame cannot become a
              different one.
  land        releasing the slider outside the active window (or clicking
              anywhere on the timeline) lands a 300-frame window starting
              there and the loop starts — the 10 s tuning loop is the
              default gesture, not a button. A
              sequential frontier fills it into RAM at the sequential rate
              (~120 fps measured) while nearest-cached serves drags, so the
              window is interactive well before it is covered. No persist
              button exists: completed 96-frame chunks stream to disk
              behind the fill, and a revisited window refills from its own
              chunks at cut speed instead of re-paying the original.
  tune        a signal slider that means nothing except invalidation: each
              change debounces, then re-pays decode-free DIS over the
              covered window in the background — the felt version of the
              slider-vs-commit fork exp05 priced at ~1.7 s per 300 frames.
              "flow preempts fill" hands the frontier's decode bandwidth to
              the signal, which is the priority inversion the plan calls
              for when the user touches tuning while crops still grow.
  jump        land a second window while the first one's chunks are still
              encoding — the seam both halves of which are priced solo but
              whose overlap is not. Jump back and feel the cut serve what
              RAM evicted.

Every request logs task, route and ms on one session clock, and every
background activity — fill, write-behind encodes, flow — logs its span, so
the graphs read as a story: a latency timeline colored by route over an
activity gantt (what was running when), and a route comparison panel (how
good each tier is). The video carries live text overlays of the same
ledger, so background signal math is visible the moment it starts. "walk session" scripts the whole story: hunt on both
routes, land A, scrub it while filling, tune twice, jump to B mid-encode,
shrink RAM, return to A on chunks. Logs land beside the storage explorer's
in explorer-logs/, keyed by tool name.

Run:
    uv run --group experiments python experiments/storage-experiments/session-explorer.py
"""

from __future__ import annotations

import json
import queue
import random
import sys
import threading
import time
from collections import OrderedDict, deque
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import av
import cv2
import numpy as np

# the fill and encode threads churn the GIL hard enough to starve the GUI
# thread for 100-400 ms at the default 5 ms switch interval — measured with
# a heartbeat probe; a shorter interval trades a little throughput for the
# event loop staying alive
sys.setswitchinterval(0.002)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import matplotlib

# Agg only, never a Qt canvas: rasterizing the session figure (text glyphs
# and point transforms, per a stall-stack watchdog) cost 150-400 ms on the
# GUI thread per redraw. Figures render on a worker thread into a pixmap.
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE  # noqa: E402

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
PROXY = FOOTAGE / "derived" / "proxy-1328-intra.mp4"
#: the app must build its own proxy — a fresh project has none. Segments on
#: the absolute chunk grid, each usable the moment ffmpeg finishes it, so
#: the timeline gets fast piece by piece while kf-snap covers the rest.
#: Durable across sessions: the proxy depends only on the source file.
PROXY_SEG_DIR = FOOTAGE / "derived" / "proxy-seg"
#: per-process — a smoke run beside a live GUI must not wipe its chunks
CHUNK_DIR = FOOTAGE / "derived" / f"_session-chunks-{__import__('os').getpid()}"
LOGS = Path(__file__).resolve().parent / "explorer-logs"

WINDOW = 300            #: the 10 s tuning window, in frames
CHUNK_FRAMES = 96       #: persist chunk (GOP x4 — results/02-*); windows
                        #: snap to this grid so chunks tile them exactly
GOP = 24
NEAR_RADIUS = 12        #: nearest-cached serves within this many frames
CROP_RECT = [2144, 982, 1024, 1024]  #: x, y, w, h in original pixels —
                                     #: mutable: the user draws it
MIN_CROP = 64
STEP_WITHIN = 60        #: step forward instead of seeking within this many
                        #: frames (exp02: the crossover on the uncut source)
DEBOUNCE_MS = 300       #: signal slider settles this long before flow runs
EVENT_CAP = 20_000
TASK_MARKERS = {"hunt": "x", "drag": "o", "play": ".", "step": "^",
                "open": "s", "hop": "P", "scrub": "d"}
ROUTE_COLORS = {"hit": "#2ca02c", "near": "#98c010", "cut": "#1f77b4",
                "proxy": "#17becf", "lo": "#9467bd", "kf": "#ff9310",
                "wait": "#aaaaaa", "miss": "#d62728"}
ACT_ROWS = {"fill": 0, "encode": 1, "flow": 2, "proxy": 3}
ACT_COLORS = {"fill": "#1f77b4", "encode": "#909090", "flow": "#c218c2",
              "proxy": "#17becf"}


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _luma(frame) -> np.ndarray:
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    return arr.reshape(frame.height, plane.line_size)[:, : frame.width]


def _crop(full: np.ndarray) -> np.ndarray:
    x, y, w, h = CROP_RECT
    return np.ascontiguousarray(full[y : y + h, x : x + w])


class Fetcher:
    """One open container on the original, absolute frame indices.

    Sequential requests step the decoder forward instead of seeking —
    without this, a play through the miss path costs the random-access
    price per frame."""

    def __init__(self):
        self.container = av.open(str(BIG))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)
        self._decoded = None
        self._pos: int | None = None

    def exact(self, idx: int) -> np.ndarray:
        if self._decoded is not None and self._pos is not None:
            ahead = idx - self._pos
            if 0 < ahead <= STEP_WITHIN:
                try:
                    for _ in range(ahead):
                        frame = next(self._decoded)
                    self._pos = idx
                    return _crop(_luma(frame))
                except StopIteration:
                    pass  # ran off the end; fall through to a real seek
        target = self.pts_of(idx)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        for frame in self._decoded:
            if frame.pts is not None and frame.pts + half >= target:
                self._pos = idx
                return _crop(_luma(frame))
        raise RuntimeError(f"off the end at {idx}")

    def keyframe(self, idx: int) -> tuple[np.ndarray, np.ndarray, int]:
        """One decode, no roll-forward. Returns (full, crop, landed) — the
        crop is the free admission the hunt route makes possible."""
        target = self.pts_of(idx)
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        frame = next(self._decoded)
        landed = round((frame.pts - (self.stream.start_time or 0))
                       / self.step)
        self._pos = landed
        full = np.ascontiguousarray(_luma(frame))
        return full, _crop(full), landed

    def close(self) -> None:
        self.container.close()


class ProxyFetcher:
    """The display-size intra proxy: the hunt's fast route. Display only —
    its pixels are the wrong form for the crop tier (a small frame cannot
    be upscaled into a big one), so this route never feeds the store."""

    def __init__(self):
        self.container = av.open(str(PROXY))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)

    def frame(self, idx: int) -> np.ndarray:
        target = self.pts_of(idx)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        for frame in self.container.decode(self.stream):
            if frame.pts is not None and frame.pts + half >= target:
                return np.ascontiguousarray(_luma(frame))
        raise RuntimeError(f"proxy off the end at {idx}")

    def close(self) -> None:
        self.container.close()


class SegmentProxy:
    """The proxy arriving in pieces: 96-frame intra segments on the absolute
    grid, written by a background ffmpeg. A segment is trusted once a newer
    one exists (ffmpeg has moved on) or the build has exited; the one still
    being written is not readable and is never touched."""

    def __init__(self):
        self._open: OrderedDict[int, av.container.InputContainer] = OrderedDict()
        self._usable: set[int] = set()   #: segment indices safe to read
        self._lock = threading.Lock()

    @staticmethod
    def _path(seg: int) -> Path:
        return PROXY_SEG_DIR / f"seg-{seg:05d}.mp4"

    def refresh(self, exclude: int | None = None) -> int:
        """Rescan the directory; returns how many segments are usable.
        `exclude` is the segment ffmpeg holds open right now — with a
        batch scheduler the file being written is not simply the newest
        index, so the builder names it explicitly."""
        present = {int(p.stem.split("-")[1])
                   for p in PROXY_SEG_DIR.glob("seg-*.mp4")}
        present.discard(exclude)
        with self._lock:
            self._usable = present
        return len(present)

    def fetch(self, idx: int) -> np.ndarray | None:
        seg, rel = idx // CHUNK_FRAMES, idx % CHUNK_FRAMES
        with self._lock:
            if seg not in self._usable:
                return None
            if seg not in self._open:
                try:
                    self._open[seg] = av.open(str(self._path(seg)))
                except OSError:
                    self._usable.discard(seg)
                    return None
                while len(self._open) > 3:
                    _, old = self._open.popitem(last=False)
                    old.close()
            self._open.move_to_end(seg)
            container = self._open[seg]
            stream = container.streams.video[0]
            pts_of, step = _pts_helpers(stream)
            target = pts_of(rel)
            half = step / 2
            container.seek(target, stream=stream)
            for frame in container.decode(stream):
                if frame.pts is not None and frame.pts + half >= target:
                    return np.ascontiguousarray(_luma(frame))
        return None

    def close(self) -> None:
        with self._lock:
            for container in self._open.values():
                container.close()
            self._open.clear()


def _launch_proxy_build(total: int, rate: Fraction, start_seg: int = 0,
                        n_segs: int | None = None) -> "subprocess.Popen":
    """One ffmpeg, separate process (measured nearly free for the
    foreground), segmenting as it goes. Splits land exactly on the chunk
    grid because -g 1 makes every frame a keyframe, and a resumed build's
    -ss is frame-accurate (half a frame early, so the first emitted frame
    is exactly start_seg*96 — exp06 verified the alignment)."""
    import subprocess
    PROXY_SEG_DIR.mkdir(parents=True, exist_ok=True)
    start_frame = start_seg * CHUNK_FRAMES
    flags = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
    cmd = ["ffmpeg", "-y"]
    if start_frame:
        ss = float((Fraction(start_frame) - Fraction(1, 2)) / rate)
        cmd += ["-ss", f"{ss:.6f}"]
    n_frames = total - start_frame
    if n_segs is not None:
        n_frames = min(n_segs * CHUNK_FRAMES, n_frames)
    splits = ",".join(str(f) for f in
                      range(CHUNK_FRAMES, n_frames, CHUNK_FRAMES))
    cmd += ["-i", str(BIG),
            "-vf", "scale=1328:-2",
            "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-g", "1",
            "-fps_mode", "passthrough", "-an",
            "-frames:v", str(n_frames)]
    if splits:
        cmd += ["-f", "segment", "-segment_frames", splits,
                "-reset_timestamps", "1",
                "-segment_start_number", str(start_seg),
                str(PROXY_SEG_DIR / "seg-%05d.mp4")]
    else:  # a single-segment batch needs no muxer
        cmd += [str(PROXY_SEG_DIR / f"seg-{start_seg:05d}.mp4")]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=flags)


BUILD_BATCH = 4     #: segments per invocation — exp06: +5% wall over one
                    #: linear pass, and position completely free
REDIRECT_SEGS = 8   #: a commit farther than this from the running batch
                    #: kills it (~1.3 s to the first segment at the new spot)


class ProxyBuilder:
    """exp06's verdict, wired: the proxy builds in 4-segment batches
    ordered by distance from attention, redirected when a landing commits
    far from the running batch, never racing a fill for the original
    (the decoder collapse), resuming across sessions for free because the
    schedule is just 'whichever batches are missing, nearest first'."""

    def __init__(self, total: int, rate: Fraction, expected: int,
                 act_start, act_end):
        self.total, self.rate, self.expected = total, rate, expected
        self.proc = None
        self.batch: tuple[int, int] | None = None
        self.attention = 0
        self._act = None
        self._act_start, self._act_end = act_start, act_end
        self._launching = False   #: a spawn thread is in flight
        self._stopped = False

    @staticmethod
    def _present() -> set[int]:
        return {int(p.stem.split("-")[1])
                for p in PROXY_SEG_DIR.glob("seg-*.mp4")}

    def _incomplete(self) -> list[tuple[int, int]]:
        present = self._present()
        return [(s, min(BUILD_BATCH, self.expected - s))
                for s in range(0, self.expected, BUILD_BATCH)
                if any(i not in present
                       for i in range(s, min(s + BUILD_BATCH, self.expected)))]

    def writing_seg(self) -> int | None:
        """The file ffmpeg holds open right now — never trust it."""
        if self.proc is None or self.batch is None:
            return None
        s, n = self.batch
        in_range = [i for i in self._present() if s <= i < s + n]
        return max(in_range) if in_range else None

    def _kill(self, why: str) -> None:
        victim = self.writing_seg()
        self.proc.terminate()
        self.proc.wait()
        self.proc = None
        if victim is not None:  # a truncated victim would serve short
            (PROXY_SEG_DIR / f"seg-{victim:05d}.mp4").unlink(missing_ok=True)
        s, n = self.batch if self.batch else (0, 0)
        self._act_end(self._act, f"batch @{s} x{n}: {why}")
        self._act = None

    def commit(self, seg: int) -> None:
        """Attention committed somewhere; redirect if the running batch is
        far and there is nearer work to do."""
        self.attention = seg
        if self.proc is None or self.batch is None or \
                self.proc.poll() is not None:
            return
        s, n = self.batch
        here = abs(seg - (s + n // 2))
        if here <= REDIRECT_SEGS:
            return
        remaining = self._incomplete()
        if remaining and min(abs(seg - (bs + bn // 2))
                             for bs, bn in remaining) < here:
            self._kill("redirected")

    def tick(self, fill_running: bool) -> bool:
        """Advance the schedule; True while a batch is running."""
        if self._launching:
            return True
        if self.proc is not None:
            if self.proc.poll() is None:
                return True
            self.proc = None
            self._act_end(self._act)
            self._act = None
        if fill_running:
            return False  # attention first: never race a fill
        remaining = self._incomplete()
        if not remaining:
            return False
        s, n = min(remaining,
                   key=lambda b: abs(self.attention - (b[0] + b[1] // 2)))
        self.batch = (s, n)
        self._act = self._act_start("proxy", f"batch @{s} x{n}")
        # process creation blocks for hundreds of ms on Windows (measured
        # 1.86 s worst on the GUI thread) — spawn from a worker
        self._launching = True

        def spawn():
            proc = _launch_proxy_build(self.total, self.rate, s, n)
            if self._stopped:
                proc.terminate()
            self.proc = proc
            self._launching = False

        threading.Thread(target=spawn, daemon=True).start()
        return True

    def done(self) -> bool:
        return not self._launching and self.proc is None \
            and not self._incomplete()

    def stop(self) -> None:
        self._stopped = True  # a spawn in flight terminates on arrival
        if self.proc is not None and self.proc.poll() is None:
            self._kill("stopped: session closed")


class Store:
    """Budget-capped LRU of crop frames keyed by absolute index. The lock
    is for the fill thread; every op under it is a dict touch, never a
    decode."""

    def __init__(self, budget: int):
        self.budget = budget
        self.d: OrderedDict[int, np.ndarray] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, idx: int):
        with self.lock:
            if idx in self.d:
                self.d.move_to_end(idx)
                return self.d[idx]
        return None

    def nearest(self, idx: int):
        with self.lock:
            if not self.d:
                return None
            best = min(self.d, key=lambda k: abs(k - idx))
            if abs(best - idx) <= NEAR_RADIUS:
                return best, self.d[best]
        return None

    def put(self, idx: int, arr: np.ndarray) -> None:
        with self.lock:
            self.d[idx] = arr
            self.d.move_to_end(idx)
            while len(self.d) > self.budget:
                self.d.popitem(last=False)

    def covered(self, start: int, end: int) -> list[int]:
        with self.lock:
            return sorted(k for k in self.d if start <= k < end)

    def set_budget(self, budget: int) -> None:
        with self.lock:
            self.budget = budget
            while len(self.d) > budget:
                self.d.popitem(last=False)

    def __len__(self):
        return len(self.d)


class ChunkStore:
    """Write-behind persistence: one intra file per 96-frame chunk on the
    absolute grid. A chunk is the unit of persistence, eviction and
    coverage, and 'which chunks exist' is an explicit record read from the
    directory, never inferred from a gap."""

    def __init__(self):
        self._open: OrderedDict[int, av.container.InputContainer] = OrderedDict()
        self._lock = threading.Lock()
        CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _path(start: int) -> Path:
        return CHUNK_DIR / f"chunk-{start:06d}.mp4"

    def persisted(self) -> set[int]:
        return {int(p.stem.split("-")[1]) for p in CHUNK_DIR.glob("chunk-*.mp4")}

    def encode(self, start: int, frames: list[np.ndarray]) -> None:
        path = self._path(start)
        with av.open(str(path), "w") as out:
            stream = out.add_stream("libx264", rate=24)
            stream.height, stream.width = frames[0].shape
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": "18", "preset": "veryfast", "g": "1"}
            for arr in frames:
                vf = av.VideoFrame.from_ndarray(arr, format="gray")
                vf = vf.reformat(format="yuv420p")
                for pkt in stream.encode(vf):
                    out.mux(pkt)
                time.sleep(0.001)  # yield: the GUI thread breathes between
            for pkt in stream.encode():  # frames, ~0.1 s per chunk total
                out.mux(pkt)

    def fetch(self, idx: int) -> np.ndarray | None:
        start = idx - idx % CHUNK_FRAMES
        with self._lock:
            if start not in self._open:
                path = self._path(start)
                if not path.exists():
                    return None
                self._open[start] = av.open(str(path))
                while len(self._open) > 3:
                    _, old = self._open.popitem(last=False)
                    old.close()
            self._open.move_to_end(start)
            container = self._open[start]
            stream = container.streams.video[0]
            pts_of, step = _pts_helpers(stream)
            target = pts_of(idx - start)
            half = step / 2
            container.seek(target, stream=stream)
            for frame in container.decode(stream):
                if frame.pts is not None and frame.pts + half >= target:
                    return np.ascontiguousarray(_luma(frame))
        return None

    def wipe(self) -> None:
        with self._lock:
            for container in self._open.values():
                container.close()
            self._open.clear()
        for path in CHUNK_DIR.glob("chunk-*.mp4"):
            try:
                path.unlink(missing_ok=True)
            except OSError:  # an encoder mid-write; the dir dies with us
                pass

    def destroy(self) -> None:
        self.wipe()
        try:
            CHUNK_DIR.rmdir()
        except OSError:
            pass


class WindowFill:
    """The landing sequence: fill [start, end) into RAM chunk by chunk.

    Chunks the store already holds refill from disk at cut speed; the rest
    decode the original at the sequential rate and stream to the encoder
    queue as they complete. `pause` is the priority inversion — flow sets
    it and the frontier yields its decode bandwidth."""

    def __init__(self, start: int, end: int, anchor: int, cache: Store,
                 store: ChunkStore, encode_q: queue.Queue, on_covered):
        self.start, self.end = start, end
        self.anchor = max(start, min(anchor, end - 1))
        self.cache = cache
        self.store = store
        self.encode_q = encode_q
        self.on_covered = on_covered
        self.pause = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.pos = start

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def launch(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, wait: bool = True) -> None:
        """wait=False signals and returns: the dying frontier's last frames
        land in the same cache at the same form, which is harmless — only a
        form change must actually wait for it."""
        self._stop.set()
        self.pause.clear()
        if self._thread and wait:
            self._thread.join(timeout=15)
        self._thread = None

    def _wait_if_paused(self) -> None:
        while self.pause.is_set() and not self._stop.is_set():
            time.sleep(0.05)

    def _run(self) -> None:
        t0 = time.perf_counter()
        persisted = self.store.persisted()
        from_chunks = from_original = 0
        paused_s = 0.0
        fetcher: Fetcher | None = None
        # attention-first: fill from the playhead's chunk to the end, then
        # wrap — the loop starts where the user clicked, and at ~3x the
        # play rate the frontier stays ahead of it instead of behind it
        chunks = list(range(self.start, self.end, CHUNK_FRAMES))
        first = min((self.anchor - self.start) // CHUNK_FRAMES,
                    len(chunks) - 1)
        chunks = chunks[first:] + chunks[:first]
        try:
            for cstart in chunks:
                if self._stop.is_set():
                    return
                cend = min(cstart + CHUNK_FRAMES, self.end)
                if cstart in persisted:
                    for idx in range(cstart, cend):
                        if self._stop.is_set():
                            return
                        self._wait_if_paused()
                        arr = self.store.fetch(idx)
                        if arr is None:  # chunk vanished; re-derive below
                            break
                        self.cache.put(idx, arr)
                        self.pos = idx
                        from_chunks += 1
                    else:
                        continue
                if fetcher is None:
                    fetcher = Fetcher()
                target = fetcher.pts_of(cstart)
                half = fetcher.step / 2
                fetcher.container.seek(target, stream=fetcher.stream)
                buffer: list[np.ndarray] = []
                idx = cstart
                for frame in fetcher.container.decode(fetcher.stream):
                    if self._stop.is_set():
                        return
                    p0 = time.perf_counter()
                    self._wait_if_paused()
                    paused_s += time.perf_counter() - p0
                    if frame.pts is None or frame.pts + half < target:
                        continue
                    arr = _crop(_luma(frame))
                    buffer.append(arr)
                    self.cache.put(idx, arr)
                    self.pos = idx
                    from_original += 1
                    idx += 1
                    if idx >= cend:
                        break
                if len(buffer) == cend - cstart:
                    self.encode_q.put((cstart, buffer))
            wall = time.perf_counter() - t0
            self.on_covered(self.start, wall, from_chunks, from_original,
                            paused_s)
        finally:
            if fetcher is not None:
                fetcher.close()


def _route_key(route: str) -> str:
    return route.split(" ")[0].split("Δ")[0]


def _render_session_figure(events: list[dict], activity: list[dict],
                           now: float, size_px: tuple[int, int]):
    """Runs on a worker thread: pure matplotlib/Agg, no Qt objects.
    Returns (rgba bytes, w, h, png bytes) for the GUI to display and for
    --fig to save."""
    fig = Figure(figsize=(size_px[0] / 100, size_px[1] / 100), dpi=100,
                 layout="constrained")
    gs = fig.add_gridspec(3, 1, height_ratios=[3.2, 1.0, 2.2], hspace=0.12)
    ax_lat = fig.add_subplot(gs[0])
    ax_act = fig.add_subplot(gs[1], sharex=ax_lat)
    ax_cmp = fig.add_subplot(gs[2])

    # panel 1: the session — every request in time, colored by route
    by_route: dict[str, tuple[list, list]] = {}
    for e in events:
        key = _route_key(e["route"])
        by_route.setdefault(key, ([], []))
        by_route[key][0].append(e["t"])
        by_route[key][1].append(max(e["ms"], 0.005))
    for key, (xs, ys) in sorted(by_route.items()):
        if len(xs) > 1200:  # point transforms are the other draw cost;
            stride = len(xs) // 1200  # stats below still use everything
            xs, ys = xs[::stride], ys[::stride]
        ax_lat.scatter(xs, ys, s=12, alpha=0.65,
                       color=ROUTE_COLORS.get(key, "#777777"),
                       label=key, linewidths=0)
    for band, label in ((100, "felt"), (16, "frame")):
        ax_lat.axhline(band, color="#999999", lw=0.7, ls=":")
        ax_lat.annotate(f"{label} {band}ms", (0.998, band),
                        xycoords=("axes fraction", "data"),
                        fontsize=6, color="#777777",
                        ha="right", va="bottom")
    for a in activity:
        if a["what"] in ("window", "crop"):
            for ax in (ax_lat, ax_act):
                ax.axvline(a["t0"], color="#555555", lw=0.7, ls="--",
                           alpha=0.6)
            ax_lat.annotate(a["detail"], (a["t0"], 0.99),
                            xycoords=("data", "axes fraction"),
                            fontsize=6, color="#555555", rotation=90,
                            ha="right", va="top")
    ax_lat.set_yscale("log")
    ax_lat.grid(True, which="both", alpha=0.2)
    if by_route:
        ax_lat.legend(fontsize=7, loc="upper right", ncols=len(by_route),
                      frameon=False)
    ax_lat.set_ylabel("ms (log)")
    ax_lat.tick_params(labelbottom=False)
    ax_lat.set_title("the session: request latency by route, over what "
                     "ran behind it", fontsize=9)

    # panel 2: what was running when — the background gantt
    for a in activity:
        row = ACT_ROWS.get(a["what"])
        if row is None:
            continue
        t1 = a["t1"] if a["t1"] is not None else now
        ax_act.broken_barh(
            [(a["t0"], max(t1 - a["t0"], 0.03))], (row + 0.15, 0.7),
            facecolors=ACT_COLORS[a["what"]],
            alpha=0.5 if a["t1"] is not None else 0.9)
    ax_act.set_ylim(0, len(ACT_ROWS))
    ax_act.set_yticks([r + 0.5 for r in ACT_ROWS.values()])
    ax_act.set_yticklabels(list(ACT_ROWS), fontsize=7)
    ax_act.grid(True, axis="x", alpha=0.2)
    ax_act.set_xlabel("session time (s)")
    ax_act.invert_yaxis()

    # panel 3: how good each tier is — p50 bar, p95 whisker, per route
    order = sorted(by_route, key=lambda k: float(
        np.median(by_route[k][1])))
    p50s, p95s = [], []
    for key in order:
        ys = np.array(by_route[key][1])
        p50s.append(float(np.median(ys)))
        p95s.append(float(np.percentile(ys, 95)))
    ypos = np.arange(len(order))
    ax_cmp.barh(ypos, p50s, height=0.6, color=[
        ROUTE_COLORS.get(k, "#777777") for k in order], alpha=0.8)
    ax_cmp.hlines(ypos, p50s, p95s, color="#555555", lw=1.2)
    ax_cmp.scatter(p95s, ypos, marker="|", s=60, color="#555555")
    for i, key in enumerate(order):
        n = len(by_route[key][1])
        ax_cmp.annotate(
            f" n={n}  p50 {p50s[i]:.3g}  p95 {p95s[i]:.3g}",
            (max(p95s[i], p50s[i]), i), fontsize=7, va="center",
            color="#444444")
    ax_cmp.set_yticks(ypos)
    ax_cmp.set_yticklabels(order, fontsize=8)
    ax_cmp.set_xscale("log")
    ax_cmp.grid(True, axis="x", which="both", alpha=0.2)
    ax_cmp.set_xlabel("ms (log) — bar p50, whisker to p95")
    ax_cmp.invert_yaxis()

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    w, h = canvas.get_width_height()
    rgba = bytes(canvas.buffer_rgba())
    import io
    png = io.BytesIO()
    fig.savefig(png, format="png", dpi=110)
    return rgba, w, h, png.getvalue()


class CropCanvas(QLabel):
    """The frame view, with a rubber-band crop gesture. Emits the drawn
    rectangle in label coordinates; the explorer owns the mapping back to
    source pixels, because only it knows what the label is showing."""

    drawn = Signal(int, int, int, int)  # x, y, w, h in label coords

    def __init__(self):
        super().__init__(alignment=Qt.AlignmentFlag.AlignCenter)
        from PySide6.QtWidgets import QRubberBand
        self._band = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self._origin = None

    def mousePressEvent(self, event) -> None:
        self._origin = event.position().toPoint()
        from PySide6.QtCore import QRect
        self._band.setGeometry(QRect(self._origin, self._origin))
        self._band.show()

    def mouseMoveEvent(self, event) -> None:
        if self._origin is not None:
            from PySide6.QtCore import QRect
            self._band.setGeometry(
                QRect(self._origin, event.position().toPoint()).normalized())

    def mouseReleaseEvent(self, event) -> None:
        if self._origin is None:
            return
        rect = self._band.geometry()
        self._band.hide()
        self._origin = None
        if rect.width() > 8 and rect.height() > 8:  # a drag, not a click
            self.drawn.emit(rect.x(), rect.y(), rect.width(), rect.height())


class JumpSlider(QSlider):
    """A timeline you can click: press jumps the thumb to the cursor, then
    the normal drag machinery takes over."""

    def mousePressEvent(self, event) -> None:
        from PySide6.QtWidgets import QStyle
        value = QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(),
            int(event.position().x()), self.width())
        self.setValue(value)
        super().mousePressEvent(event)


class RunLog:
    """Everything one phase of the session was asked to do this launch.
    Event times share the session clock, so phases plot on one axis."""

    def __init__(self, config: str, t0: float):
        self.config = config
        self.label = config
        self.started = datetime.now(timezone.utc).isoformat()
        self._t0 = t0
        self.events: list[dict] = []
        self.walls: list[dict] = []
        self.capped = False
        self._steady = 0    #: play-hits are a constant 0.01 ms; a looping
        self.suppressed = 0  #: session floods tens of thousands of them and
                             #: the graph/save cost of the flood is what
                             #: freezes the GUI — keep 1 in 8, count the rest

    def log(self, task: str, frame: int, route: str, ms: float) -> None:
        if task == "play" and ms < 20 \
                and route.split(" ")[0] in ("hit", "proxy", "lo", "wait"):
            self._steady += 1
            if self._steady % 8:
                self.suppressed += 1
                return
        if len(self.events) >= EVENT_CAP:
            self.capped = True
            return
        self.events.append({
            "t": round(time.perf_counter() - self._t0, 4),
            "task": task, "frame": frame, "route": route, "ms": round(ms, 3)})

    def summary(self) -> dict:
        by_task: dict[str, dict] = {}
        for task in TASK_MARKERS:
            samples = [e["ms"] for e in self.events if e["task"] == task]
            if samples:
                by_task[task] = {"n": len(samples), **{
                    k: round(v, 2)
                    for k, v in harness.quantiles(samples).items()}}
        routes: dict[str, int] = {}
        for e in self.events:
            key = e["route"].split(" ")[0]
            routes[key] = routes.get(key, 0) + 1
        return {"label": self.label, "config": self.config,
                "by_task": by_task, "routes": routes, "walls": self.walls,
                "suppressed_play_hits": self.suppressed,
                "events_capped": self.capped}

    def stats_text(self) -> str:
        s = self.summary()
        lines = [self.label]
        for task, q in s["by_task"].items():
            lines.append(f"  {task:<5} n={q['n']:<5} p50={q['p50']:>8.1f}"
                         f"  p95={q['p95']:>8.1f}  max={q['max']:>8.1f} ms")
        lines.append("  routes: " + "  ".join(
            f"{k}={v}" for k, v in sorted(s["routes"].items())))
        for w in self.walls[-4:]:
            lines.append(f"  {w['what']}: {w['wall_s']:.2f}s ({w['detail']})")
        return "\n".join(lines)


class SessionExplorer(QMainWindow):
    #: worker threads report through queued signals — a widget touched from
    #: a worker thread is the crash, not a style point
    covered = Signal(int, float, int, int, float)
    flow_done = Signal(float, int, int)
    work_failed = Signal(str)
    graphs_ready = Signal(object)

    def __init__(self):
        super().__init__()
        self.covered.connect(self._window_covered)
        self.flow_done.connect(self._flow_landed)
        self.work_failed.connect(self._work_broke)
        self.graphs_ready.connect(self._graphs_landed)
        self._graph_rendering = False
        self._graph_dirty = False
        self._last_graph_png: bytes | None = None
        self.setWindowTitle("session explorer — hunt, land, tune, jump")
        self.resize(1680, 900)
        with av.open(str(BIG)) as c:
            stream = c.streams.video[0]
            self.rate = stream.average_rate  # exact, for the resume -ss
            self.fps = float(stream.average_rate)
            self.orig_w, self.orig_h = stream.width, stream.height
            self.total = (stream.frames or int(
                stream.duration * stream.time_base * stream.average_rate))
        self.total -= GOP  # the last GOP's decodability is not guaranteed
        self.t0 = time.perf_counter()   #: the session clock everything shares
        self.activity: list[dict] = []  #: background spans: fill/encode/flow
        self.act_lock = threading.Lock()
        self._fill_act: dict | None = None
        self._flow_act: dict | None = None
        self._flow_started = 0.0
        self._flow_value = 0
        self._encoding_chunk: int | None = None
        self._last_image: np.ndarray | None = None
        self._last_graph = 0.0
        self._last_save = 0.0
        self.cache = Store(600)
        self.store = ChunkStore()
        self.miss_fetcher = Fetcher()
        self.hunt_fetcher = Fetcher()
        #: --cold simulates a fresh project: no hand-made proxy, no
        #: segments — the app must earn its own fast timeline
        cold = "--cold" in sys.argv
        if cold:
            for p in PROXY_SEG_DIR.glob("seg-*.mp4"):
                p.unlink(missing_ok=True)
        self.proxy = ProxyFetcher() if PROXY.exists() and not cold else None
        self.segproxy: SegmentProxy | None = None
        self.builder: ProxyBuilder | None = None
        self._seg_expected = -(-self.total // CHUNK_FRAMES)
        self._seg_have = 0
        self._proxy_pending = False
        self._proxy_announced = False
        self._covered_once = False
        if self.proxy is None:
            self.segproxy = SegmentProxy()
            self._seg_have = self.segproxy.refresh()
            # attention outranks the timeline: the build waits until the
            # first fill is done — two software decoders on the original
            # collapse each other (measured: opening fill 7.1 s vs 3.6 s)
            self._proxy_pending = self._seg_have < self._seg_expected
        self.fill: WindowFill | None = None
        self.windows: list[int] = []       #: starts, chunk-aligned
        self.active: tuple[int, int] | None = None
        self._encode_q: queue.Queue = queue.Queue()
        self._encoding_now = [0]  # chunks queued or mid-encode
        threading.Thread(target=self._encode_loop, daemon=True).start()
        self._flow_busy = False
        self._flow_dirty = False
        self.admitted_free = 0
        self.pos = 0
        self.run: RunLog | None = None
        self.runs: dict[str, RunLog] = {}
        self._busy = False
        self._queue: deque[int] = deque()
        self._recent: deque[float] = deque(maxlen=30)
        self._rng = random.Random()
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._play_tick)
        self._scrubbing = False  #: finger down on the timeline
        self._scrub_timer = QTimer(self)
        self._scrub_timer.timeout.connect(self._scrub_tick)
        self._scrub_targets: list[int] = []
        self._debounce = QTimer(self, singleShot=True, interval=DEBOUNCE_MS)
        self._debounce.timeout.connect(self._flow_fire)
        LOGS.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS / f"session-explorer-{stamp}.json"
        #: provenance costs two subprocesses (git, ffmpeg) — probed once;
        #: re-probing per autosave was a 2 s GUI stall every 30 s
        self._provenance = {
            "tool": "session-explorer.py",
            "sieve_rev": harness._sieve_rev(),
            "machine": harness._machine(),
            "versions": harness._versions(),
        }
        self._graph_timer = QTimer(self, singleShot=True, interval=600)
        self._graph_timer.timeout.connect(self._redraw_graphs)
        self._save_timer = QTimer(self, singleShot=True, interval=2500)
        self._save_timer.timeout.connect(self._save_log)
        self._hud_timer = QTimer(self, interval=500)
        self._hud_timer.timeout.connect(self._refresh_status)
        self._hud_timer.start()

        self.hunt_box = QComboBox()
        self.hunt_box.addItems(["hunt: proxy", "hunt: kf-snap"])
        # even cold, the proxy route stays selectable: it serves whatever
        # segments exist and falls through to kf for the rest
        self.hunt_box.setToolTip(
            "how requests outside any window are served. proxy = the "
            "display-size intra file (5-9 ms drags, display-only pixels); "
            "kf-snap = one decode of the original (~130 ms, wrong by up to "
            "half a GOP — but the full frame's crop is admitted to RAM for "
            "free, so hunting on this route pre-warms wherever you linger).")
        self.budget_spin = QSpinBox()
        self.budget_spin.setRange(100, 2400)
        self.budget_spin.setValue(600)
        self.budget_spin.setSuffix(" frames RAM")
        self.budget_spin.setToolTip(
            "crop-frame budget (~1 MB each). Two windows fit at the "
            "default; shrink it after jumping and feel the old window "
            "evict down onto its chunks.")
        self.budget_spin.valueChanged.connect(
            lambda v: self.cache.set_budget(v))
        self.preempt = QCheckBox("flow preempts fill")
        self.preempt.setChecked(True)
        self.preempt.setToolTip(
            "the plan's priority inversion: touching the signal pauses the "
            "fill frontier so flow gets the machine. Uncheck to feel them "
            "share instead; the flow wall records paused fill time either "
            "way.")
        self.signal_slider = QSlider(Qt.Orientation.Horizontal)
        self.signal_slider.setRange(1, 10)
        self.signal_slider.setValue(5)
        self.signal_slider.setMaximumWidth(160)
        self.signal_slider.setToolTip(
            "a signal parameter that means nothing except invalidation: "
            f"each change waits {DEBOUNCE_MS} ms, then re-pays decode-free "
            "DIS over the covered window in the background. The HUD prints "
            "how long the graphs stayed stale — the felt slider-vs-commit "
            "answer.")
        self.signal_slider.valueChanged.connect(self._signal_changed)
        self.signal_label = QLabel("signal=5")
        self.reset_btn = QPushButton("reset cold")
        self.reset_btn.setToolTip(
            "drop RAM, chunks and windows — back to a cold hunt.")
        self.reset_btn.clicked.connect(self._reset)

        self.window_btn = QPushButton("window here")
        self.window_btn.setToolTip(
            f"claim a {WINDOW}-frame window at the playhead (snapped to the "
            "chunk grid) and start filling it. Landing on an old window's "
            "ground refills from its chunks at cut speed.")
        self.window_btn.clicked.connect(lambda: self._land_at(self.pos))
        self.window_box = QComboBox()
        self.window_box.addItem("windows…")
        self.window_box.setToolTip(
            "every window this session has landed; pick one to jump back. "
            "The seam — old chunks still encoding while the new fill runs — "
            "is the unmeasured overlap this explorer exists to feel.")
        self.window_box.activated.connect(self._window_picked)
        self.play_btn = QPushButton("play")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self._toggle_play)
        self.pause_btn = QPushButton("pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setToolTip(
            "the marked exception. The loop is the default state — it runs "
            "whenever a window exists and nothing else claims the playhead. "
            "Pause (space) is for staring at one frame; arrows step while "
            "paused. Relocating the window resumes the loop.")
        self.pause_btn.setStyleSheet(
            "QPushButton:checked { background: #b33; color: white; }")
        self.pause_btn.toggled.connect(self._toggle_pause)
        self.hop_btn = QPushButton("hop")
        self.hop_btn.setCheckable(True)
        self.hop_btn.setToolTip("uniform-random frames inside the active "
                                "window — sustained random access through "
                                "the stack")
        self.hop_btn.toggled.connect(self._toggle_hop)
        self.scrub_btn = QPushButton("scripted scrub")
        self.scrub_btn.setToolTip(
            "the lingering scrub (gaussian around a jumping anchor) at "
            "20 Hz, 100 fetches, confined to the active window — the same "
            "hands the harness used.")
        self.scrub_btn.clicked.connect(self._scripted_scrub)
        self.walk_btn = QPushButton("walk session")
        self.walk_btn.setToolTip(
            "script the whole story: hunt on both routes, land window A, "
            "scrub it while it fills, tune the signal twice, jump to a far "
            "window B mid-encode, shrink RAM, return to A on its chunks. "
            "Every leg lands in the graphs and stats as its own phase.")
        self.walk_btn.clicked.connect(self._walk)

        row1 = QHBoxLayout()
        for w in (self.hunt_box, self.budget_spin, self.preempt,
                  QLabel("signal"), self.signal_slider, self.signal_label):
            row1.addWidget(w)
        row1.addStretch(1)
        row1.addWidget(self.reset_btn)
        row2 = QHBoxLayout()
        for w in (self.window_btn, self.window_box):
            row2.addWidget(w)
        row2.addStretch(1)
        for w in (self.play_btn, self.pause_btn, self.hop_btn,
                  self.scrub_btn, self.walk_btn):
            row2.addWidget(w)
        top = QVBoxLayout()
        top.addLayout(row1)
        top.addLayout(row2)

        self._view = "full"     #: what the canvas shows: full frame or crop
        self._pix_w = self._pix_h = 0
        self.canvas = CropCanvas()
        self.canvas.setMinimumSize(280, 180)
        # a QLabel's size hint follows its pixmap; when the view swaps
        # aspect (hunt full-frame vs crop) or a graph render lands, that
        # hint reflows the splitter and the video visibly resizes — the
        # felt "jitter on swap-over". Pixmaps must never drive layout.
        self.canvas.setSizePolicy(QSizePolicy.Policy.Ignored,
                                  QSizePolicy.Policy.Ignored)
        self.canvas.setStyleSheet("background: #101010;")
        self.canvas.setToolTip(
            "drag a rectangle on the full-frame hunt view to draw the "
            "crop. A new crop is a form change: RAM, chunks and windows "
            "all invalidate, because a stored frame of the old form "
            "cannot become the new one.")
        self.canvas.drawn.connect(self._crop_drawn)
        self.slider = JumpSlider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setMaximum(self.total - 1)
        self.slider.setToolTip(
            "click anywhere to jump; release outside the active window "
            "lands a fresh window there and the loop starts.")
        self.slider.sliderMoved.connect(lambda i: self.request(i, "drag"))
        self.slider.valueChanged.connect(lambda i: self.request(i, "drag"))
        self.slider.sliderPressed.connect(self._scrub_began)
        self.slider.sliderReleased.connect(self._released)
        self.coverage = QLabel("")
        self.coverage.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 8pt; color: #6a6;")
        self.hud = QLabel("cold: the whole timeline, no windows — hunt")
        self.hud.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10pt; padding: 3px;")
        self.status = QLabel("")
        self.status.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 9pt; color: #888;")
        # text length must not drive layout either: the HUD and coverage
        # strings change every half-second, and their size hints were
        # nudging the splitter — the other half of the felt jitter
        for lbl in (self.coverage, self.hud, self.status):
            lbl.setSizePolicy(QSizePolicy.Policy.Ignored,
                              QSizePolicy.Policy.Fixed)
        self.window_box.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.window_box.setMinimumContentsLength(16)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addLayout(top)
        left_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(self.slider)
        left_layout.addWidget(self.coverage)
        left_layout.addWidget(self.hud)
        left_layout.addWidget(self.status)

        self.graph_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.graph_label.setMinimumSize(400, 300)
        self.graph_label.setSizePolicy(QSizePolicy.Policy.Ignored,
                                       QSizePolicy.Policy.Ignored)
        self.graph_label.setStyleSheet("background: #ffffff;")
        self.stats = QPlainTextEdit(readOnly=True)
        self.stats.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 9pt;")
        save_lbl = QLabel(f"log: {self.log_path.name}")
        save_lbl.setStyleSheet("color: #888; font-size: 8pt;")
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.graph_label, 3)
        right_layout.addWidget(self.stats, 2)
        right_layout.addWidget(save_lbl)
        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([760, 920])
        self.setCentralWidget(splitter)
        self.request(0, "open")
        # there is no stopped state: the app opens looping. Pausing is the
        # marked exception (space), never the default the user starts in.
        self._land_at(0)

    # ── the activity ledger ──────────────────────────────────────────────
    def _now(self) -> float:
        return time.perf_counter() - self.t0

    def _act_start(self, what: str, detail: str = "") -> dict:
        entry = {"what": what, "t0": round(self._now(), 3), "t1": None,
                 "detail": detail}
        with self.act_lock:
            self.activity.append(entry)
        return entry

    def _act_end(self, entry: dict | None, detail: str | None = None) -> None:
        if entry is None or entry["t1"] is not None:
            return
        entry["t1"] = round(self._now(), 3)
        if detail:
            entry["detail"] = detail

    def _mark(self, what: str, detail: str) -> None:
        t = round(self._now(), 3)
        with self.act_lock:
            self.activity.append(
                {"what": what, "t0": t, "t1": t, "detail": detail})

    # ── phases and runs ──────────────────────────────────────────────────
    def _in_window(self, idx: int) -> bool:
        return self.active is not None and \
            self.active[0] <= idx < self.active[1]

    def _config_for(self, idx: int) -> str:
        if self._in_window(idx):
            parts = [f"window@{self.active[0]}",
                     f"crop={CROP_RECT[2]}x{CROP_RECT[3]}",
                     f"b={self.budget_spin.value()}"]
            if not self.preempt.isChecked():
                parts.append("no-preempt")
            return " ".join(parts)
        route = self.hunt_box.currentText().replace("hunt: ", "")
        return f"hunt {route}"

    def _run_for(self, idx: int) -> RunLog:
        config = self._config_for(idx)
        if config not in self.runs:
            self.runs[config] = RunLog(config, self.t0)
        self.run = self.runs[config]
        return self.run

    # ── the stack, one request at a time ─────────────────────────────────
    def _with_rect(self, full: np.ndarray) -> np.ndarray:
        """The crop rectangle drawn onto a full-frame view, at its scale."""
        s = full.shape[1] / self.orig_w
        x, y, w, h = CROP_RECT
        out = full.copy()
        cv2.rectangle(out, (round(x * s), round(y * s)),
                      (round((x + w) * s), round((y + h) * s)),
                      255, max(1, round(full.shape[1] / 700)))
        return out

    def _display_frame(self, idx: int) -> np.ndarray | None:
        """The display tier, whichever form it exists in: the whole-file
        proxy, or whatever segments the background build has finished."""
        if self.proxy is not None:
            return self.proxy.frame(idx)
        if self.segproxy is not None:
            return self.segproxy.fetch(idx)
        return None

    def _serve(self, idx: int, task: str, exact: bool) -> tuple[np.ndarray, str]:
        if not self._in_window(idx):
            self._view = "full"
            if self.hunt_box.currentIndex() == 0:
                shown = self._display_frame(idx)
                if shown is not None:
                    return self._with_rect(shown), "proxy"
            full, crop, landed = self.hunt_fetcher.keyframe(idx)
            self.cache.put(landed, crop)  # free bytes are never refused
            self.admitted_free += 1
            return self._with_rect(full), f"kf Δ{idx - landed}"
        self._view = "crop"
        got = self.cache.get(idx)
        if got is not None:
            return got, "hit"
        from_disk = self.store.fetch(idx)
        if from_disk is not None:
            self.cache.put(idx, from_disk)
            return from_disk, "cut"
        if not exact:
            # progressive refinement: a nearly-right cached frame first, a
            # low-res placeholder second, and the same frame at full form
            # arrives when the fill catches up. A blocking miss on the GUI
            # thread is what "frozen" feels like; only exact requests
            # (slider release) are allowed to pay it.
            near = self.cache.nearest(idx)
            if near is not None and abs(near[0] - idx) <= 3:
                best, arr = near
                return arr, f"near Δ{idx - best}"
            lo = self._display_frame(idx)
            if lo is not None:
                s = lo.shape[1] / self.orig_w
                x, y, cw, ch = CROP_RECT
                piece = lo[round(y * s) : round((y + ch) * s),
                           round(x * s) : round((x + cw) * s)]
                if piece.size:
                    return np.ascontiguousarray(cv2.resize(
                        piece, (cw, ch),
                        interpolation=cv2.INTER_NEAREST)), "lo"
            if near is not None:
                best, arr = near
                return arr, f"near Δ{idx - best}"
            # nothing presentable and nothing owed: hold the current frame
            # and let the fill arrive. Cold landings used to block the GUI
            # 300-450 ms per play-miss here; a short hold reads as a beat,
            # a blocked event loop reads as a hang.
            return None, "wait"
        arr = self.miss_fetcher.exact(idx)
        self.cache.put(idx, arr)
        return arr, "miss"

    def request(self, idx: int, task: str = "step", exact: bool = False) -> None:
        idx = max(0, min(self.total - 1, idx))
        self._queue.clear()  # coalesce always: the measured foreground shape
        self._queue.append(idx)
        if self._busy:
            return
        self._busy = True
        try:
            while self._queue:
                target = self._queue.popleft()
                run = self._run_for(target)
                try:
                    before = time.perf_counter()
                    image, route = self._serve(target, task, exact)
                    ms = (time.perf_counter() - before) * 1000
                except Exception as exc:  # noqa: BLE001
                    self.hud.setText(f"frame {target}: {exc}")
                    continue
                if image is None:  # a hold, not a serve: the playhead
                    run.log(task, target, route, ms)  # stays put
                    continue
                self.pos = target
                self._show(image)
                run.log(task, target, route, ms)
                self._recent.append(ms)
                mean = sum(self._recent) / len(self._recent)
                self.hud.setText(
                    f"frame {target:>6} · {task:<5} · {route:<9}"
                    f" · {ms:7.1f} ms · last {len(self._recent)} mean "
                    f"{mean:6.1f} ms")
                self.slider.blockSignals(True)
                self.slider.setValue(target)
                self.slider.blockSignals(False)
                QApplication.processEvents()
        finally:
            self._busy = False
            self._touch()

    def _overlay_lines(self) -> list[str]:
        """The live ledger, as the video sees it: what runs right now."""
        lines = []
        if self.pause_btn.isChecked():
            lines.append("PAUSED  [space] resume  [arrows] step")
        if self.fill and self.fill.running():
            done = self.fill.pos - self.fill.start
            span = self.fill.end - self.fill.start
            state = " PAUSED by flow" if self.fill.pause.is_set() else ""
            lines.append(f"FILL {done}/{span} @{self.fill.pos}{state}")
        queued = self._encoding_now[0]
        chunk = self._encoding_chunk
        if chunk is not None:
            extra = f" (+{queued - 1} queued)" if queued > 1 else ""
            lines.append(f"WRITE-BEHIND chunk@{chunk}{extra}")
        if self._flow_busy:
            elapsed = self._now() - self._flow_started
            lines.append(f"FLOW signal={self._flow_value} {elapsed:.1f}s")
        elif self._debounce.isActive():
            lines.append("SIGNAL settling...")
        if self.builder is not None and self.builder.proc is not None:
            at = self.builder.batch[0] if self.builder.batch else 0
            lines.append(f"PROXY BUILD {self._seg_have}/{self._seg_expected}"
                         f" batch@{at}")
        return lines

    def _show(self, image: np.ndarray) -> None:
        if not image.flags.c_contiguous:
            image = np.ascontiguousarray(image)
        self._last_image = image
        lines = self._overlay_lines()
        if lines:
            image = image.copy()
            fs = max(0.5, image.shape[1] / 1800)
            pitch = round(34 * fs)
            for i, text in enumerate(lines):
                org = (round(12 * fs), pitch * (i + 1))
                cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                            fs, 0, max(2, round(4 * fs)), cv2.LINE_AA)
                cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                            fs, 255, max(1, round(1.5 * fs)), cv2.LINE_AA)
        h, w = image.shape
        qimage = QImage(image.data, w, h, image.strides[0],
                        QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage).scaled(
            self.canvas.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation)
        self._pix_w, self._pix_h = pixmap.width(), pixmap.height()
        self.canvas.setPixmap(pixmap)

    # ── windows ──────────────────────────────────────────────────────────
    def _released(self) -> None:
        """The landing gesture: release inside the active window is a
        tuning scrub (paused stays paused); release anywhere else commits
        attention there — the window relocates and the loop resumes,
        clearing any pause, because moving attention means wanting motion."""
        self._scrubbing = False
        value = self.slider.value()
        self.request(value, "drag", exact=True)
        if not self._in_window(value):
            self._land_at(value)
        self._drive()

    def _land_at(self, pos: int) -> None:
        # the click is the START of the 10 s window: the user clicks where
        # something begins and wants the ten seconds after it, not five
        # seconds of lead-up
        self._set_window(pos, anchor=pos)
        self._scrubbing = False
        self.pause_btn.setChecked(False)
        self._drive()

    def _set_window(self, at: int, anchor: int | None = None) -> None:
        # the loop's bounds are exactly the ten seconds the user asked for;
        # the FILL range is the chunk-grid superset of them, because the
        # chunk store lives on the absolute grid and a window must not
        # bend the grid to itself
        start = max(0, min(at, self.total - WINDOW))
        end = min(start + WINDOW, self.total)
        if self.active == (start, end):
            return
        if self.fill:
            self.fill.stop(wait=False)  # landing must not wait on the old
            self._act_end(self._fill_act, "stopped: window switched")
        self.active = (start, end)
        self._mark("window", f"@{start}")
        if self.builder is not None:  # a landing is committed attention:
            self.builder.commit(start // CHUNK_FRAMES)  # redirect the build
        if start not in self.windows:
            self.windows.append(start)
            secs = start / self.fps
            self.window_box.addItem(f"window @{start} ({secs:.0f}s)")
        run = self._run_for(start)
        overlap = self._encoding_now[0]
        run.walls.append({
            "what": "window-open", "wall_s": 0.0,
            "detail": f"chunks-still-encoding={overlap}"})
        fill_lo = start - start % CHUNK_FRAMES
        fill_hi = min(-(-end // CHUNK_FRAMES) * CHUNK_FRAMES, self.total)
        self.fill = WindowFill(
            fill_lo, fill_hi, start if anchor is None else anchor,
            self.cache, self.store, self._encode_q,
            lambda *a: self.covered.emit(*a))
        self.fill.config = run.config  # walls land on the run that launched
        self._fill_act = self._act_start("fill", f"@{start}")
        self.fill.launch()
        self.hud.setText(
            f"window @{start}: filling — drag it now, nearest serves while "
            "the frontier races you")
        # stay on the frame the user committed to; only move if it's outside
        self.request(self.pos if start <= self.pos < end else start, "step")

    def _window_picked(self, row: int) -> None:
        if row <= 0 or row > len(self.windows):
            return
        self._set_window(self.windows[row - 1])

    def _window_covered(self, start: int, wall: float, from_chunks: int,
                        from_original: int, paused_s: float) -> None:
        self._act_end(self._fill_act,
                      f"@{start}: {from_chunks}ch/{from_original}orig")
        self._covered_once = True
        config = getattr(self.fill, "config", None) \
            if self.fill and self.fill.start == start else None
        if config is None:
            config = next(
                (c for c in self.runs if c.startswith(f"window@{start}")),
                None)
        if config:
            self.runs[config].walls.append({
                "what": "covered", "wall_s": round(wall, 2),
                "detail": f"{from_chunks} from chunks, {from_original} from "
                          f"original, fill paused {paused_s:.2f}s"})
        self.hud.setText(
            f"window @{start} covered in {wall:.2f}s "
            f"({from_chunks} refilled from chunks, {from_original} decoded) "
            "— write-behind trails, tune away")
        self._touch()

    # ── write-behind ─────────────────────────────────────────────────────
    def _encode_loop(self) -> None:
        while True:
            start, frames = self._encode_q.get()
            self._encoding_now[0] = self._encode_q.qsize() + 1
            self._encoding_chunk = start
            entry = self._act_start("encode", f"chunk@{start}")
            try:
                self.store.encode(start, frames)
            except Exception:  # noqa: BLE001 — a failed chunk re-derives
                pass
            self._act_end(entry)
            self._encoding_chunk = None
            self._encoding_now[0] = self._encode_q.qsize()

    # ── the drawn crop ───────────────────────────────────────────────────
    def _crop_drawn(self, lx: int, ly: int, lw: int, lh: int) -> None:
        if self._view != "full" or not self._pix_w:
            self.hud.setText("draw the crop on the full-frame hunt view — "
                             "jump outside the window first")
            return
        off_x = (self.canvas.width() - self._pix_w) / 2
        off_y = (self.canvas.height() - self._pix_h) / 2
        sx = self.orig_w / self._pix_w
        sy = self.orig_h / self._pix_h
        x = round((lx - off_x) * sx)
        y = round((ly - off_y) * sy)
        w, h = round(lw * sx), round(lh * sy)
        x = max(0, min(x, self.orig_w - MIN_CROP))
        y = max(0, min(y, self.orig_h - MIN_CROP))
        w = max(MIN_CROP, min(w, self.orig_w - x))
        h = max(MIN_CROP, min(h, self.orig_h - y))
        x, y, w, h = (v - v % 2 for v in (x, y, w, h))  # yuv420 wants even
        self._apply_crop(x, y, w, h)

    def _apply_crop(self, x: int, y: int, w: int, h: int) -> None:
        """A new crop is a form change: everything derived from the old
        one — RAM frames, chunks, windows — invalidates. The hunt tiers
        (proxy, kf) survive; they never depended on the crop."""
        self.play_btn.setChecked(False)
        self.hop_btn.setChecked(False)
        if self.fill:
            self.fill.stop()
            self.fill = None
        self._act_end(self._fill_act, "stopped: crop changed")
        while not self._encode_q.empty():
            try:
                self._encode_q.get_nowait()
            except queue.Empty:
                break
        self.active = None
        self.windows.clear()
        self.window_box.clear()
        self.window_box.addItem("windows…")
        self.cache = Store(self.budget_spin.value())
        self.store.wipe()
        self.admitted_free = 0
        CROP_RECT[:] = [x, y, w, h]
        self._mark("crop", f"{w}x{h}+{x}+{y}")
        self.hud.setText(
            f"crop drawn: {w}x{h}+{x}+{y} — old form dropped everywhere; "
            "relanding the loop on the new form")
        self._land_at(self.pos)  # the app never stops: new form, same place

    # ── signal / flow ────────────────────────────────────────────────────
    def _signal_changed(self, value: int) -> None:
        self.signal_label.setText(f"signal={value}")
        if self.active is None:
            return
        self._debounce.start()

    def _flow_fire(self) -> None:
        if self.active is None:
            return
        if self._flow_busy:
            self._flow_dirty = True
            return
        covered = self.cache.covered(*self.active)
        # flow between non-adjacent frames is garbage across the gaps:
        # compute over the longest CONTIGUOUS covered run, not the set
        runs, run_start = [], 0
        for i in range(1, len(covered) + 1):
            if i == len(covered) or covered[i] != covered[i - 1] + 1:
                runs.append(covered[run_start:i])
                run_start = i
        covered = max(runs, key=len) if runs else []
        if len(covered) < 2:
            self.hud.setText("signal: window not filled enough for flow yet")
            return
        self._flow_busy = True
        preempt = self.preempt.isChecked()
        if preempt and self.fill and self.fill.running():
            self.fill.pause.set()
        with self.cache.lock:
            arrays = [self.cache.d[k] for k in covered if k in self.cache.d]
        value = self.signal_slider.value()
        self._flow_started = self._now()
        self._flow_value = value
        self._flow_act = self._act_start(
            "flow", f"signal={value}"
                    f"{' preempting fill' if preempt else ''}")
        self.hud.setText(f"signal={value}: flow over {len(arrays)} frames…")

        def worker():
            try:
                dis = cv2.DISOpticalFlow_create(
                    cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
                before = time.perf_counter()
                prev = arrays[0]
                for cur in arrays[1:]:
                    flow = dis.calc(prev, cur, None)
                    float(np.mean(np.abs(flow)))
                    prev = cur
                wall = time.perf_counter() - before
            except Exception as exc:  # noqa: BLE001
                self.work_failed.emit(f"flow: {exc!r}"[:200])
                return
            self.flow_done.emit(wall, len(arrays), value)

        threading.Thread(target=worker, daemon=True).start()

    def _flow_landed(self, wall: float, n: int, value: int) -> None:
        self._flow_busy = False
        self._act_end(self._flow_act, f"signal={value} n={n}")
        if self.fill:
            self.fill.pause.clear()
        if self.active is not None:
            config = self._config_for(self.active[0])
            if config in self.runs:
                self.runs[config].walls.append({
                    "what": "flow", "wall_s": round(wall, 2),
                    "detail": f"signal={value} n={n} "
                              f"preempt={'on' if self.preempt.isChecked() else 'off'}"})
        self.hud.setText(
            f"signal={value}: graphs were stale {wall:.2f}s over {n} frames "
            "— the slider-vs-commit number, felt")
        self._touch()
        if self._flow_dirty:
            self._flow_dirty = False
            self._debounce.start()

    def _work_broke(self, err: str) -> None:
        self._flow_busy = False
        self._act_end(self._flow_act, "failed")
        if self.fill:
            self.fill.pause.clear()
        self.hud.setText(f"background work failed: {err}")

    # ── drives ───────────────────────────────────────────────────────────
    # There is no stopped state. The transport resolves to one mode:
    # paused and scrub are exceptions the user is actively holding open,
    # play and hop are harness drives, and everything else falls through
    # to the loop — the default the app always returns to.
    def _mode(self) -> str:
        if self.pause_btn.isChecked():
            return "paused"
        if self._scrubbing:
            return "scrub"
        if self.play_btn.isChecked():
            return "play"
        if self.hop_btn.isChecked():
            return "hop"
        return "loop" if self.active else "idle"

    def _toggle_pause(self, on: bool) -> None:
        if on:
            self.play_btn.setChecked(False)
            self.hop_btn.setChecked(False)
        self._drive()

    def _toggle_play(self, on: bool) -> None:
        if on:
            self.pause_btn.setChecked(False)
            self.hop_btn.setChecked(False)
        self._drive()

    def _toggle_hop(self, on: bool) -> None:
        if on:
            self.pause_btn.setChecked(False)
            self.play_btn.setChecked(False)
        self._drive()

    def _scrub_began(self) -> None:
        self._scrubbing = True
        self._drive()

    def _drive(self) -> None:
        mode = self._mode()
        if mode in ("paused", "scrub", "idle"):
            self._play_timer.stop()
            return
        # the loop is the product gesture, so it runs at video rate;
        # play and hop stay free-run to feel throughput
        self._play_timer.start(
            max(1, round(1000 / self.fps)) if mode == "loop" else 0)

    def _play_tick(self) -> None:
        if self._busy:
            return
        mode = self._mode()
        if mode == "hop":
            if self.active is None:
                self.hop_btn.setChecked(False)
                return
            self.request(self._rng.randrange(*self.active), "hop")
            return
        if mode == "loop":
            nxt = self.pos + 1
            if not self._in_window(nxt):
                nxt = self.active[0]
            self.request(nxt, "play")
            return
        if mode == "play":
            nxt = self.pos + 1
            if nxt >= self.total:
                self.play_btn.setChecked(False)
                return
            self.request(nxt, "play")
            return
        self._play_timer.stop()  # mode changed under the timer

    def _scripted_scrub(self) -> None:
        lo, hi = self.active if self.active else (0, self.total)
        rng = random.Random(7)
        targets, anchor = [], rng.randrange(lo, hi)
        for _ in range(100):
            if rng.random() < 0.12:
                anchor = rng.randrange(lo, hi)
            targets.append(max(lo, min(hi - 1, round(rng.gauss(anchor, 8)))))
        self._scrub_targets = targets
        self._scrub_timer.start(50)

    def _scrub_tick(self) -> None:
        if not self._scrub_targets:
            self._scrub_timer.stop()
            self.hud.setText("scripted scrub done — stats compare phases")
            return
        if self._busy:
            return
        self.request(self._scrub_targets.pop(0), "scrub")

    # ── the walk: the whole session, scripted ────────────────────────────
    def _announce(self, text: str) -> None:
        self.hud.setText(text)
        self.hud.repaint()
        QApplication.processEvents()

    def _walk_scrub(self, n: int = 60, seed: int = 7,
                    pace_s: float = 0.03) -> None:
        lo, hi = self.active if self.active else (0, self.total)
        rng = random.Random(seed)
        anchor = rng.randrange(lo, hi)
        for _ in range(n):
            if rng.random() < 0.12:
                anchor = rng.randrange(lo, hi)
            target = max(lo, min(hi - 1, round(rng.gauss(anchor, 8))))
            self.request(target, "scrub")
            QApplication.processEvents()
            time.sleep(pace_s)

    def _walk_wait_covered(self, timeout_s: float = 60.0) -> bool:
        if self.active is None:
            return False
        lo, hi = self.active
        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            if len(self.cache.covered(lo, hi)) >= hi - lo:
                return True
            if self.fill and not self.fill.running():
                break
            QApplication.processEvents()
            time.sleep(0.05)
        return len(self.cache.covered(lo, hi)) >= hi - lo

    def _walk_wait_flow(self, timeout_s: float = 30.0) -> None:
        deadline = time.perf_counter() + timeout_s
        while (self._flow_busy or self._debounce.isActive()) \
                and time.perf_counter() < deadline:
            QApplication.processEvents()
            time.sleep(0.05)

    def _walk(self) -> None:
        if self._busy:
            return
        self.walk_btn.setEnabled(False)
        rng = random.Random(11)
        try:
            # leg 1: hunt on both routes — the finding-the-clip phase
            self._reset()
            hunts = [rng.randrange(self.total) for _ in range(15)]
            if self.proxy is not None:
                self.hunt_box.setCurrentIndex(0)
                self._announce("[walk] hunting on the proxy — jumps are "
                               "single-digit ms")
                for idx in hunts:
                    self.request(idx, "hunt")
                    QApplication.processEvents()
                    time.sleep(0.05)
            self.hunt_box.setCurrentIndex(1)
            self._announce("[walk] hunting on kf-snap — ~130 ms, but every "
                           "jump admits a crop frame for free")
            for idx in hunts[:8]:
                self.request(idx, "hunt")
                QApplication.processEvents()
                time.sleep(0.05)
            if self.proxy is not None:
                self.hunt_box.setCurrentIndex(0)

            # leg 2: land window A and scrub it while it fills
            a = self.total // 3
            self._announce("[walk] landing window A — scrubbing before the "
                           "fill finishes: nearest serves, misses thin out")
            self._set_window(a)
            self._walk_scrub(60, seed=7)
            if not self._walk_wait_covered():
                self._announce("[walk] window A never covered; stopping")
                return
            self._walk_scrub(30, seed=8)

            # leg 3: tune — two debounced flow re-pays, preempt on
            self._announce("[walk] tuning: signal slider twice, flow "
                           "preempting fill")
            self.preempt.setChecked(True)
            for v in (7, 3):
                self.signal_slider.setValue(v)
                self._walk_wait_flow()

            # leg 4: jump far to window B while A's chunks still encode
            b = min(2 * self.total // 3, self.total - WINDOW)
            self._announce("[walk] jumping to window B — the seam: A's "
                           "write-behind still runs while B fills")
            self._set_window(b)
            self._walk_scrub(50, seed=9)
            if not self._walk_wait_covered():
                self._announce("[walk] window B never covered; stopping")
                return

            # leg 5: shrink RAM, return to A — chunks serve what RAM lost
            self._announce("[walk] shrinking RAM to one window and "
                           "returning to A — routes go cut, not miss")
            self.budget_spin.setValue(WINDOW)
            self._set_window(a)
            self._walk_scrub(40, seed=10)
            self._walk_wait_covered()
            for _ in range(25):
                self.request(rng.randrange(*self.active), "hop")
                QApplication.processEvents()
                time.sleep(0.02)
            self._save_log(force=True)
            self._redraw_graphs()
            self._announce("[walk] done — stats compare hunt, A cold, B "
                           "seam, A revisited; walls carry the overlap "
                           "facts")
        finally:
            self.walk_btn.setEnabled(True)

    # ── reset / status / graphs / log ────────────────────────────────────
    def _reset(self) -> None:
        if self.fill:
            self.fill.stop()
            self.fill = None
        self._act_end(self._fill_act, "stopped: reset")
        while not self._encode_q.empty():
            try:
                self._encode_q.get_nowait()
            except queue.Empty:
                break
        self.active = None
        self.windows.clear()
        self.window_box.clear()
        self.window_box.addItem("windows…")
        self.cache = Store(self.budget_spin.value())
        self.store.wipe()
        self.admitted_free = 0
        self.pos = 0
        self.hud.setText("cold again — relanding the loop at the start")
        self._land_at(0)  # there is no stopped state, even after a reset
        self._touch()

    def _refresh_status(self) -> None:
        # gate on a real first coverage, not on fill state — the opening
        # request's processEvents fired this timer before the fill object
        # even existed, launching the build straight into the collapse
        if self._proxy_pending and (self._covered_once or self._now() > 20):
            self._proxy_pending = False
            self.builder = ProxyBuilder(self.total, self.rate,
                                        self._seg_expected,
                                        self._act_start, self._act_end)
            self.builder.attention = self.pos // CHUNK_FRAMES
        if self.builder is not None:
            fill_running = self.fill is not None and self.fill.running()
            self.builder.tick(fill_running)
            self._seg_have = self.segproxy.refresh(self.builder.writing_seg())
            if self.builder.done() and not self._proxy_announced:
                self._proxy_announced = True
                self.hud.setText(
                    f"proxy complete: {self._seg_have} segments — the whole "
                    "timeline is fast now")
        elif self.segproxy is not None:
            self._seg_have = self.segproxy.refresh()
        # keep overlays current while nothing is being requested — a flow
        # or encode finishing must vanish from the frame without a scrub
        if not self._busy and self._last_image is not None \
                and not self._play_timer.isActive():
            self._show(self._last_image)
        blocks = 72
        per = self.total / blocks
        with self.cache.lock:
            dense = set(self.cache.d.keys())
        persisted = self.store.persisted()

        def cell(b: int) -> str:
            lo, hi = int(b * per), int((b + 1) * per)
            if any(lo <= k < hi for k in dense):
                return "█"    # in RAM, exact
            if any(lo <= s < hi or lo < s + CHUNK_FRAMES <= hi
                   for s in persisted):
                return "▄"    # on disk, ~10 ms away
            if any(w < hi and w + WINDOW > lo for w in self.windows):
                return "·"    # a claimed window, not yet materialized
            return " "

        bar = "".join(cell(b) for b in range(blocks))
        active = f"@{self.active[0]}" if self.active else "none"
        fill_state = ""
        if self.fill and self.fill.running():
            fill_state = (" · fill@"
                          f"{self.fill.pos}"
                          f"{' (paused)' if self.fill.pause.is_set() else ''}")
        self.coverage.setText(
            f"[{bar}] ram {len(dense)} · chunks {len(persisted)} · "
            f"window {active}{fill_state} · encoding {self._encoding_now[0]}"
            f" · free-admits {self.admitted_free}")
        self.status.setText(self._config_for(self.pos))

    def _touch(self) -> None:
        if not self._graph_timer.isActive():
            self._graph_timer.start()
        if not self._save_timer.isActive():
            self._save_timer.start()

    def _ordered_runs(self) -> list[RunLog]:
        return [r for r in self.runs.values() if r.events or r.walls]

    def _redraw_graphs(self) -> None:
        # the loop is the default state now, so graphs must update under
        # it — throttled; the actual rasterizing runs on a worker thread
        # because Agg text/transform drawing cost 150-400 ms on the GUI
        # thread (stall-stack watchdog), which felt like frozen playback
        if self._busy:
            self._graph_timer.start(1200)
            return
        if self._play_timer.isActive()                 and time.perf_counter() - self._last_graph < 5.0:
            self._graph_timer.start(1200)
            return
        if self._graph_rendering:
            self._graph_dirty = True
            return
        self._last_graph = time.perf_counter()
        runs = self._ordered_runs()
        events = [e for r in runs for e in r.events]
        with self.act_lock:
            activity = [dict(a) for a in self.activity]
        now = self._now()

        # stats text is cheap — build it here, on current data
        by_route: dict[str, list[float]] = {}
        for e in events:
            by_route.setdefault(_route_key(e["route"]), []).append(
                max(e["ms"], 0.005))
        header = ["session by route:"]
        for key in sorted(by_route, key=lambda k: float(
                np.median(by_route[k]))):
            ys = by_route[key]
            header.append(
                f"  {key:<6} n={len(ys):<5}"
                f" p50={float(np.median(ys)):>8.2f}"
                f"  p95={float(np.percentile(ys, 95)):>8.1f} ms")
        self.stats.setPlainText(
            "\n".join(header) + "\n\n"
            + "\n\n".join(r.stats_text() for r in runs))

        if not events:
            return
        size = (max(500, self.graph_label.width()),
                max(360, self.graph_label.height()))
        self._graph_rendering = True

        def worker():
            try:
                result = _render_session_figure(events, activity, now, size)
            except Exception:  # noqa: BLE001 — a failed frame of graphs
                result = None  # just means the next one draws instead
            self.graphs_ready.emit(result)

        threading.Thread(target=worker, daemon=True).start()

    def _graphs_landed(self, result) -> None:
        self._graph_rendering = False
        if result is not None:
            rgba, w, h, png = result
            self._last_graph_png = png
            image = QImage(rgba, w, h, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(image.copy())
            if pixmap.size() != self.graph_label.size():
                pixmap = pixmap.scaled(  # render was at dispatch-time size
                    self.graph_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            self.graph_label.setPixmap(pixmap)
        if self._graph_dirty:
            self._graph_dirty = False
            self._graph_timer.start(300)


    def _save_log(self, force: bool = False) -> None:
        # dumping a long session's JSON stalls the GUI thread; while the
        # loop drives, save at most every 30 s and catch up when idle
        if not force and (self._busy or (
                self._play_timer.isActive()
                and time.perf_counter() - self._last_save < 30)):
            self._save_timer.start(5000)
            return
        self._last_save = time.perf_counter()
        with self.act_lock:
            activity = [dict(a) for a in self.activity]
        payload = {
            **self._provenance,
            "when": datetime.now(timezone.utc).isoformat(),
            "total_frames": self.total, "window": WINDOW, "gop": GOP,
            "crop": list(CROP_RECT),
            "activity": activity,
            "chunk_frames": CHUNK_FRAMES, "near_radius": NEAR_RADIUS,
            "runs": [
                {**run.summary(), "started": run.started,
                 "events": run.events}
                for run in self._ordered_runs()
            ],
        }
        self.log_path.write_text(json.dumps(payload, indent=1),
                                 encoding="utf-8")

    def closeEvent(self, event) -> None:
        self.play_btn.setChecked(False)
        self.hop_btn.setChecked(False)
        self._play_timer.stop()
        if self.fill:
            self.fill.stop()
        self._save_log(force=True)
        self.miss_fetcher.close()
        self.hunt_fetcher.close()
        if self.proxy:
            self.proxy.close()
        if self.builder is not None:
            self.builder.stop()  # completed segments stay usable
        if self.segproxy is not None:
            self.segproxy.close()
        self.store.destroy()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Left):
            # stepping means staring at frames: entering the marked
            # exception deliberately, one keypress at a time
            self.pause_btn.setChecked(True)
            step = 1 if key == Qt.Key.Key_Right else -1
            self.request(self.pos + step, "step")
        elif key == Qt.Key.Key_Space:
            self.pause_btn.toggle()
        else:
            super().keyPressEvent(event)


def main() -> None:
    if not BIG.exists():
        print(f"missing {BIG}")
        return
    app = QApplication.instance() or QApplication(sys.argv)
    window = SessionExplorer()
    if "--fig" in sys.argv:  # save the graphs after a headless run
        fig_path = sys.argv[sys.argv.index("--fig") + 1]
    else:
        fig_path = None
    if "--walk" in sys.argv:  # headless validation of the full walk
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        window._walk()
        if fig_path:  # graphs render async now — wait for the png
            deadline = time.perf_counter() + 20
            while window._last_graph_png is None \
                    and time.perf_counter() < deadline:
                QApplication.processEvents()
                time.sleep(0.05)
            if window._last_graph_png:
                Path(fig_path).write_bytes(window._last_graph_png)
        print(window.hud.text())
        data = json.loads(window.log_path.read_text(encoding="utf-8"))
        print(f"walk ok: {len(data['runs'])} phases logged to "
              f"{window.log_path.name}")
        if window.fill:
            window.fill.stop()
        window.store.destroy()
        return
    if "--smoke" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        window.request(5000, "hunt")          # proxy (or kf) route
        print(window.hud.text())
        window.hunt_box.setCurrentIndex(1)
        window.request(6000, "hunt")          # kf route, free admission
        print(window.hud.text())
        window._set_window(4000)              # land a window, fill races
        time.sleep(1.0)
        window.request(4010, "drag")          # near or hit mid-fill
        print(window.hud.text())
        window._walk_wait_covered(timeout_s=30)
        window.request(4200, "drag", exact=True)
        print(window.hud.text())
        window.signal_slider.setValue(8)      # debounced flow
        window._walk_wait_flow()
        print(window.hud.text())
        deadline = time.perf_counter() + 30   # let write-behind land one
        while not window.store.persisted() and time.perf_counter() < deadline:
            time.sleep(0.2)
        print(f"chunks persisted: {sorted(window.store.persisted())[:4]}")
        window._apply_crop(1000, 500, 512, 512)  # form change drops it all
        print(f"after crop: ram={len(window.cache)} "
              f"chunks={len(window.store.persisted())} "
              f"windows={len(window.windows)}")
        window._land_at(4150)                 # re-land on the new form
        window._walk_wait_covered(timeout_s=30)
        window.request(4150, "drag", exact=True)
        print(window.hud.text())
        window._refresh_status()
        print(window.coverage.text())
        window._redraw_graphs()
        window._save_log(force=True)
        data = json.loads(window.log_path.read_text(encoding="utf-8"))
        acts = {}
        for a in data["activity"]:
            acts[a["what"]] = acts.get(a["what"], 0) + 1
        print(f"activity ledger: {acts}")
        print(f"smoke ok: {len(data['runs'])} phases logged to "
              f"{window.log_path.name}")
        if window.fill:
            window.fill.stop()
        window.store.destroy()
        return
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
