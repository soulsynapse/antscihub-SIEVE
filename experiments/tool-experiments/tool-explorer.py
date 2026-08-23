"""Feel the loop with a tool on it: overlay live, series filling by watching.

Forked from `storage-experiments/session-explorer.py` and deliberately not
rewritten. The question here is what adding a tool does to a loop that has
already been measured, and that only has an answer if the loop is the same
loop — so the transport, the tier stack, the log schema and every one of the
freeze fixes come across untouched, and the existing
`session-explorer-*.json` baseline subtracts from this one.

What the fork adds, and what each is for:

  tool        one of `absdiff`, `dis`, `mhi-lag`, declaring the frames it
              needs as offsets. Everything downstream reads the
              declaration: the overlay asks for `needs(row)`, the prefetch
              asks for the same one row ahead, the sweep asks across a span.
  overlay     the field drawn over the frame, computed at analysis form
              because a threshold on a downscaled image is not the
              downscale of the threshold. Its reduction goes straight into
              the series — the field was computed to be drawn, the frame
              was hot, and the number that falls out is the one a sweep
              would have written. That is the byproduct claim, and this is
              where it is true or false.
  series      one float per frame per tool, coverage recorded rather than
              inferred, drawn as a second band under the strip. Watch it
              fill behind the playhead while you play; that band is the
              claim that watching covers ground.
  three clocks  serve, field and paint timed separately, because a
              conflated clock is how a slow overlay reads as a slow store,
              which is the day the freeze hunt cost.
  avoidable   decodes for rows a declaration said were coming. Zero, or a
              bug with an address. There is no other way to see a
              re-fetch: it looks exactly like the store being slow.

The parameter slider is the tool's own, not the old signal knob: changing it
invalidates the *series* and not the frames, which is the invalidation line
made feelable. Redrawing the crop invalidates both. If the line is where
this folder claims, the first gesture is dramatically cheaper than the
second, and if it is not, the line is drawn in the wrong place.

Five states worth driving by hand, in order: cold with a tool on and
playing; a hop into unswept ground with `mhi-lag` on, which is the prefetch
question with four specific old frames and one frame budget; switching
tools; redrawing the crop; and changing the parameter. What a script cannot
do is judge whether the overlay reads at its ceiling, whether the decimated
series band looks like signal or like noise, and whether any of it feels the
way the numbers say it should.

Inherited below, unchanged:

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
    uv run --group experiments python experiments/tool-experiments/tool-explorer.py
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE  # noqa: E402

import forms  # noqa: E402
import series as series_mod  # noqa: E402
import surfaces  # noqa: E402
import tools as toolkit  # noqa: E402

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
PROXY = FOOTAGE / "derived" / "proxy-1328-intra.mp4"
#: the app must build its own proxy — a fresh project has none. Segments on
#: the absolute chunk grid, each usable the moment ffmpeg finishes it, so
#: the timeline gets fast piece by piece while kf-snap covers the rest.
#: Durable across sessions: the proxy depends only on the source file.
PROXY_SEG_DIR = FOOTAGE / "derived" / "proxy-seg"
#: per-process — a smoke run beside a live GUI must not wipe its chunks
CHUNK_DIR = FOOTAGE / "derived" / f"_tool-chunks-{__import__('os').getpid()}"
LOGS = Path(__file__).resolve().parent / "explorer-logs"
SERIES_DIR = FOOTAGE / "derived" / "_tool-series"

#: the tools on offer, in the order the folder argues for them: one in the
#: noise beside a 5.3K decode, one forty times it, and one whose retention
#: set is not its reach. Between them every fork in the design fires.
TOOLS = {"absdiff": toolkit.absdiff,
         "dis flow": toolkit.dis_flow,
         "mhi (lags 10/20/30)": toolkit.lag_mhi}
SWEEP_CHUNK = 48    #: rows a sweep does between yields, so it can be stopped

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

    def snapshot(self) -> set[int]:
        with self._lock:
            return set(self._usable)

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


class SignalStrip:
    """The hunt's real feedback channel: per-frame motion energy over the
    display proxy, computed in the background, drawn under the timeline.
    On a fixed camera the frames cannot show where you are or where the
    behavior is — the signal can, which is the product's premise arriving
    one screen early. Energy is crop-independent (whole-frame, proxy
    resolution), so it survives crop changes untouched."""

    def __init__(self, total: int, whole_file: Path | None,
                 usable_segments):
        self.total = total
        self.energy = np.full(total, np.nan, dtype=np.float32)
        self.lock = threading.Lock()
        self.computed = 0
        self._whole = whole_file
        self._usable = usable_segments  #: callable -> set of segment starts
        self._done_segs: set[int] = set()
        self._stop = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _feed(self, start: int, lumas) -> None:
        prev = None
        vals: list[float] = []
        pos = start

        def flush() -> None:
            nonlocal vals, pos
            # incremental, and clamped: the source decodes a few more
            # frames than the demux-counted total (the 11,308 vs 11,304
            # disagreement) and the strip must not care
            end = min(pos + len(vals), self.total)
            if end > pos:
                with self.lock:
                    self.energy[pos:end] = vals[: end - pos]
                    self.computed = int(np.sum(~np.isnan(self.energy)))
            pos += len(vals)
            vals = []

        for arr in lumas:
            small = arr[::4, ::4].astype(np.int16)
            # moving-pixel area, not mean diff: the animals are a tiny
            # fraction of a fixed frame, so mean diff is sensor noise
            # (measured: p50 2.55 vs max 5.35 — flat); the fraction of
            # pixels clearing a noise floor makes sparse motion pop
            vals.append(float(np.mean(np.abs(small - prev) > 12))
                        if prev is not None else np.nan)
            prev = small
            if len(vals) >= 256:
                flush()
            if self._stop.is_set():
                break
        flush()
        with self.lock:  # the run's first diff is undefined; borrow one
            if start + 1 < self.total and np.isnan(self.energy[start]) \
                    and not np.isnan(self.energy[start + 1]):
                self.energy[start] = self.energy[start + 1]

    @staticmethod
    def _decode(path: Path):
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            for frame in container.decode(stream):
                yield _luma(frame)

    def _run(self) -> None:
        if self._whole is not None:
            self._feed(0, self._decode(self._whole))
            return
        while not self._stop.is_set() and self.computed < self.total - 1:
            fresh = sorted(self._usable() - self._done_segs)
            for seg in fresh:
                if self._stop.is_set():
                    return
                path = PROXY_SEG_DIR / f"seg-{seg:05d}.mp4"
                try:
                    self._feed(seg * CHUNK_FRAMES, self._decode(path))
                except (OSError, av.error.FFmpegError):
                    continue  # mid-write or vanished; retry next scan
                self._done_segs.add(seg)
            self._stop.wait(1.0)


class StripLabel(QLabel):
    """The strip IS the timeline: press scrubs, drag hunts along the
    signal, release lands — the same gesture grammar the slider had,
    on the element that actually shows where the behavior is."""

    pressed = Signal(float)   # 0..1 position
    moved = Signal(float)
    released = Signal()

    def _frac(self, event) -> float:
        return min(1.0, max(0.0, event.position().x() / max(1, self.width())))

    def mousePressEvent(self, event) -> None:
        self._down = True
        self.pressed.emit(self._frac(event))

    def mouseMoveEvent(self, event) -> None:
        if getattr(self, "_down", False):
            self.moved.emit(self._frac(event))

    def mouseReleaseEvent(self, event) -> None:
        if getattr(self, "_down", False):
            self._down = False
            self.released.emit()


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

    def log(self, task: str, frame: int, route: str, ms: float,
            field_ms: float = 0.0, paint_ms: float = 0.0) -> None:
        # the decimation threshold reads the serve clock only. Field and
        # paint ride along on the same event because they are the same
        # displayed frame, and separating them at read time is the whole
        # point of recording three numbers instead of their sum.
        if task == "play" and ms < 20 \
                and route.split(" ")[0] in ("hit", "proxy", "lo", "wait"):
            self._steady += 1
            if self._steady % 8:
                self.suppressed += 1
                return
        if len(self.events) >= EVENT_CAP:
            self.capped = True
            return
        event = {
            "t": round(time.perf_counter() - self._t0, 4),
            "task": task, "frame": frame, "route": route, "ms": round(ms, 3)}
        if field_ms:
            event["field_ms"] = round(field_ms, 3)
        if paint_ms:
            event["paint_ms"] = round(paint_ms, 3)
        self.events.append(event)

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


class ToolRig:
    """The active tool, its series, and the counters that judge the design.

    One place rather than fields scattered on the window, because all of it
    keys on the same pair: a series belongs to (tool, form), and switching
    either is a different series rather than a stale one. Nothing here
    touches a widget — it is the part of the explorer a headless run could
    keep.
    """

    def __init__(self, total: int, pts: np.ndarray, timebase: str):
        self.total = total
        self.pts = pts
        self.timebase = timebase
        self.name = next(iter(TOOLS))
        self.blur = 0
        self.tool = TOOLS[self.name]()
        self.series: dict[str, series_mod.Series] = {}
        self.ceilings: dict[str, float] = {}
        #: a decode for a row the declaration said was coming. The whole
        #: point of the counter is that a re-fetch is otherwise invisible —
        #: it looks exactly like the store being slow, which is what the
        #: freeze hunt spent a day discovering about something else.
        self.avoidable = 0
        self.unavoidable = 0
        self.by_watching = 0    #: series rows written by drawing a frame
        self.by_sweep = 0       #: series rows written by an asked-for sweep
        self.declared: set[int] = set()   #: last horizon's residency rows

    def use(self, name: str | None = None, blur: int | None = None) -> None:
        """Pick the tool, and the one parameter that sits above the line.

        The blur is a pre-filter on the frames the field sees, so it
        genuinely changes the answer and genuinely belongs in the key —
        unlike a threshold read off the series afterwards, which changes
        nothing upstream and must not invalidate anything. Turning it is
        the cheap gesture; redrawing the crop is the expensive one. That
        difference is the invalidation line, and if the two feel alike the
        line is in the wrong place.
        """
        if name is not None:
            self.name = name
        if blur is not None:
            self.blur = blur
        tool = TOOLS[self.name]()
        if self.blur > 0:
            k = self.blur * 2 + 1
            inner = tool.field

            def field(frames, row, _inner=inner, _k=k):
                smoothed = {r: cv2.GaussianBlur(a, (_k, _k), 0)
                            for r, a in frames.items()}
                return _inner(smoothed, row)
            tool.field = field
            tool.params = {**(tool.params or {}), "blur": self.blur}
        self.tool = tool

    def form(self, crop) -> forms.Form:
        return self.tool.form_for(tuple(crop))

    def key(self, crop) -> str:
        return f"{self.tool.key()}|{self.form(crop).key()}"

    def series_for(self, crop) -> series_mod.Series:
        """The series for this tool in this form, made if it is new.

        A tool change and a crop change both land here as a different key,
        so neither can read the other's numbers. That is the whole of
        invalidation: nothing is cleared, a different thing is named.
        """
        key = self.key(crop)
        got = self.series.get(key)
        if got is None:
            got = self.series[key] = series_mod.Series(
                source=BIG.name, tool_key=self.tool.key(),
                form_key=self.form(crop).key(), pts=self.pts,
                timebase=self.timebase)
        return got

    def ceiling_for(self, crop, value: float | None = None) -> float:
        """The top of the overlay's scale, held rather than autoscaled.

        An overlay that renormalises per frame makes a still scene look
        exactly as active as a moving one, which is a lie about the one
        quantity being tuned. So the first honest field sets the ceiling
        and later frames are drawn against it; the user raises or lowers it
        deliberately.
        """
        key = self.key(crop)
        if value is not None:
            self.ceilings[key] = value
        return self.ceilings.get(key, 0.0)

    def horizon(self, row: int, ahead: int) -> set[int]:
        """Rows the tool needs to serve `row` and the `ahead` after it.

        `needs` at a point is not a retention policy — the union over the
        run about to be served is. For sparse offsets those differ
        enormously, and holding only the point set costs a decode per
        offset per displayed frame.
        """
        return {r for step in range(max(1, ahead))
                for r in self.tool.needs(row + step)}

    def evaluate(self, row: int, frames: dict[int, np.ndarray]):
        """The field and its reduction, or None if the window is not there."""
        want = self.tool.needs(row)
        if any(frames.get(r) is None for r in want):
            return None
        got = {r: frames[r] for r in want}
        field = self.tool.field(got, row)
        return field, float(self.tool.reduce(field))


class SessionExplorer(QMainWindow):
    #: worker threads report through queued signals — a widget touched from
    #: a worker thread is the crash, not a style point
    covered = Signal(int, float, int, int, float)
    work_failed = Signal(str)
    graphs_ready = Signal(object)
    sweep_done = Signal(int)

    def __init__(self):
        super().__init__()
        self.covered.connect(self._window_covered)
        self.sweep_done.connect(self._sweep_landed)
        self.work_failed.connect(self._work_broke)
        self.graphs_ready.connect(self._graphs_landed)
        self._graph_rendering = False
        self._graph_dirty = False
        self._last_graph_png: bytes | None = None
        self.setWindowTitle("tool explorer — the loop with a tool on it")
        self.resize(1680, 900)
        with av.open(str(BIG)) as c:
            stream = c.streams.video[0]
            self.rate = stream.average_rate  # exact, for the resume -ss
            self.fps = float(stream.average_rate)
            self.orig_w, self.orig_h = stream.width, stream.height
            self.total = (stream.frames or int(
                stream.duration * stream.time_base * stream.average_rate))
        self.total -= GOP  # the last GOP's decodability is not guaranteed
        # ADR-0004: a row is a coordinate, a pts is the identity. The table
        # is built by demuxing and decoding nothing, which the keyframe-index
        # finding prices as cheap; the packet count and the row count are
        # recorded separately because on this footage they disagree, and a
        # table that hid that would be the bug the ADR was written about.
        index_t0 = time.perf_counter()
        stamps = []
        with av.open(str(BIG)) as c:
            vs = c.streams.video[0]
            self.timebase = str(vs.time_base)
            for packet in c.demux(vs):
                if packet.pts is not None:
                    stamps.append(int(packet.pts))
        stamps.sort()
        self._packets_seen = len(stamps)
        self._index_s = time.perf_counter() - index_t0
        if len(stamps) < self.total:      # pad rather than lie about length
            step = (stamps[1] - stamps[0]) if len(stamps) > 1 else 1
            last = stamps[-1] if stamps else 0
            stamps += [last + step * (i + 1)
                       for i in range(self.total - len(stamps))]
        self.rig = ToolRig(self.total, np.asarray(stamps[:self.total],
                                                  dtype=np.int64),
                           self.timebase)
        self._sweep_stop = threading.Event()
        self._sweep_busy = False
        self._last_serve_ms = 0.0
        self._last_field_ms = 0.0
        self._last_paint_ms = 0.0
        self._field_recent: deque[float] = deque(maxlen=30)
        self._paint_recent: deque[float] = deque(maxlen=30)
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
        self.strip = SignalStrip(
            self.total,
            PROXY if self.proxy is not None else None,
            (self.segproxy.snapshot if self.segproxy is not None
             else set))
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
        self._debounce.timeout.connect(self._param_fire)
        LOGS.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS / f"tool-explorer-{stamp}.json"
        #: provenance costs two subprocesses (git, ffmpeg) — probed once;
        #: re-probing per autosave was a 2 s GUI stall every 30 s
        self._provenance = {
            "tool": "tool-explorer.py",
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

        self.full_btn = QPushButton("full frame")
        self.full_btn.setCheckable(True)
        self.full_btn.setToolTip(
            "crop-space is the default everywhere — the session is about "
            "the replicate, so scrubbing previews the crop at every "
            "position. Check this to see the whole frame (with the crop "
            "outlined), which is also where a new crop gets drawn.")
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
        self.preempt = QCheckBox("sweep preempts fill")
        self.preempt.setChecked(True)
        self.preempt.setToolTip(
            "the priority inversion, now between the fill and a run the "
            "user asked for: a sweep pauses the fill frontier so it gets "
            "the machine. Uncheck to feel them share instead. Either way "
            "the paused-fill time is recorded, because a sweep that "
            "starves the loop it was launched from is the failure.")
        self.signal_slider = QSlider(Qt.Orientation.Horizontal)
        self.signal_slider.setRange(1, 8)
        self.signal_slider.setValue(1)
        self.signal_slider.setMaximumWidth(160)
        self.signal_slider.setToolTip(
            "the tool's own parameter: a pre-blur on the frames the "
            "field sees, which changes the answer and so belongs in the "
            "key. Changing it names a different series and leaves every "
            "frame where it was — the cheap half of the invalidation "
            "line. Draw a new crop for the expensive half.")
        self.signal_slider.valueChanged.connect(self._signal_changed)
        self.signal_label = QLabel("blur=0")
        self.tool_box = QComboBox()
        self.tool_box.addItems(list(TOOLS))
        self.tool_box.setToolTip(
            "the tool the overlay draws and the series stores. Switching is "
            "not a clear: a series belongs to (tool, form), so the other "
            "tool's numbers are still there and come back when you switch "
            "back. absdiff is in the noise beside a 5.3K decode and not "
            "beside a chunk; dis is roughly forty times a chunk decode; "
            "mhi-lag needs four frames spanning thirty-one, which is the "
            "one that makes a hop expensive.")
        self.tool_box.currentTextChanged.connect(self._tool_picked)
        self.overlay_btn = QPushButton("overlay")
        self.overlay_btn.setCheckable(True)
        self.overlay_btn.setChecked(True)
        self.overlay_btn.setToolTip(
            "draw the tool's field over the frame. The field is computed at "
            "analysis form and drawn at display size — a threshold on a "
            "downscaled image is not the downscale of the threshold, and "
            "what you tune against has to be what gets committed. Its "
            "reduction is written to the series on the way past, which is "
            "the byproduct claim: watching covers ground.")
        self.overlay_btn.toggled.connect(lambda _: self._repaint_current())
        self.ceiling_spin = QSpinBox()
        self.ceiling_spin.setRange(0, 255)
        self.ceiling_spin.setValue(0)
        self.ceiling_spin.setPrefix("ceil ")
        self.ceiling_spin.setToolTip(
            "top of the overlay's colour scale. 0 means take it from the "
            "first honest field and hold it. Never autoscale per frame: a "
            "still scene would look exactly as active as a moving one, "
            "which is a lie about the quantity being tuned.")
        self.ceiling_spin.valueChanged.connect(self._ceiling_changed)
        self.sweep_btn = QPushButton("sweep window")
        self.sweep_btn.setToolTip(
            "compute the tool over the active window and store the series. "
            "A button, not a background default — full processing is on the "
            "user's say. Watch the series band fill under the strip.")
        self.sweep_btn.clicked.connect(lambda: self._sweep(whole=False))
        self.sweep_all_btn = QPushButton("sweep all")
        self.sweep_all_btn.setToolTip(
            "the same over the whole timeline. This is the run you asked "
            "for, so it is allowed to make the loop worse — what it is not "
            "allowed to do is keep doing so once you go back to tuning. "
            "Click again to stop it.")
        self.sweep_all_btn.clicked.connect(lambda: self._sweep(whole=True))
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
        for w in (self.full_btn, self.hunt_box, self.budget_spin, self.preempt,
                  QLabel("param"), self.signal_slider, self.signal_label):
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
        row0 = QHBoxLayout()
        for w in (QLabel("tool"), self.tool_box, self.overlay_btn,
                  self.ceiling_spin):
            row0.addWidget(w)
        row0.addStretch(1)
        for w in (self.sweep_btn, self.sweep_all_btn):
            row0.addWidget(w)
        top = QVBoxLayout()
        top.addLayout(row0)
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
        self.strip_label = StripLabel()
        self.strip_label.setFixedHeight(88)   # two bands: energy, series
        self.strip_label.setSizePolicy(QSizePolicy.Policy.Ignored,
                                       QSizePolicy.Policy.Fixed)
        self.strip_label.setStyleSheet("background: #121212;")
        self.strip_label.setToolTip(
            "THE timeline: motion energy over the display proxy, because "
            "on a fixed camera the frames all look alike and the signal "
            "is the only thing worth scrubbing. Drag to hunt along it; "
            "release lands the loop there. Fills in as the proxy arrives; "
            "crop changes don't touch it.")
        # the hidden slider stays as the position model — every gesture
        # funnels through it, so the walk, the drives and the request
        # paths need no second navigation code path
        self._frame_of = lambda frac: int(frac * (self.total - 1))
        self.strip_label.pressed.connect(self._strip_pressed)
        self.strip_label.moved.connect(
            lambda frac: self.slider.setValue(self._frame_of(frac)))
        self.strip_label.released.connect(self._released)
        left_layout.addWidget(self.strip_label)
        self.slider.hide()
        left_layout.addWidget(self.coverage)
        left_layout.addWidget(self.hud)
        left_layout.addWidget(self.status)

        # the live series pane. Not matplotlib: rasterising a line cost
        # 16 ms for a window and 40 ms for the timeline (01-paint-cost),
        # against effectively nothing for the same data reduced to display
        # columns. Moving Agg off the GUI thread hides that from the event
        # loop and leaves it burning a core for the length of a tuning
        # loop, which here would be a third consumer inside the numbers.
        self.series_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.series_label.setMinimumHeight(150)
        self.series_label.setSizePolicy(QSizePolicy.Policy.Ignored,
                                        QSizePolicy.Policy.Ignored)
        self.series_label.setStyleSheet("background: #121212;")
        self.series_label.setToolTip(
            "the active window's series, min/max per display column. "
            "min/max rather than a mean because a one-frame spike averaged "
            "with its neighbours is a spike that never reaches the screen, "
            "and events are what this is for. Columns with nothing computed "
            "are drawn absent, never as zero.")
        self.figure_btn = QPushButton("session figure")
        self.figure_btn.setToolTip(
            "render the matplotlib story figure now. It is not on a timer: "
            "40 ms per refresh is free at save time and is not free inside "
            "a frame budget.")
        self.figure_btn.clicked.connect(lambda: self._redraw_graphs())
        self.graph_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.graph_label.setMinimumSize(400, 220)
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
        right_layout.addWidget(self.series_label, 2)
        right_layout.addWidget(self.graph_label, 3)
        right_layout.addWidget(self.stats, 2)
        fig_row = QHBoxLayout()
        fig_row.addWidget(save_lbl)
        fig_row.addStretch(1)
        fig_row.addWidget(self.figure_btn)
        right_layout.addLayout(fig_row)
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

    def _crop_of_display(self, shown: np.ndarray) -> np.ndarray | None:
        """The crop region sliced out of a display-size frame, upscaled to
        crop resolution — display-only pixels, never admitted."""
        s = shown.shape[1] / self.orig_w
        x, y, cw, ch = CROP_RECT
        piece = shown[round(y * s) : round((y + ch) * s),
                      round(x * s) : round((x + cw) * s)]
        if not piece.size:
            return None
        return np.ascontiguousarray(cv2.resize(
            piece, (cw, ch), interpolation=cv2.INTER_NEAREST))

    def _serve(self, idx: int, task: str, exact: bool) -> tuple[np.ndarray, str]:
        if not self._in_window(idx):
            # crop-space is the default everywhere: the session is about
            # the replicate, so hunting previews the crop at every
            # position; the full frame is the marked exception (a toggle),
            # summoned to see context or draw a new crop
            full_view = self.full_btn.isChecked()
            self._view = "full" if full_view else "crop"
            if self.hunt_box.currentIndex() == 0:
                shown = self._display_frame(idx)
                if shown is not None:
                    if full_view:
                        return self._with_rect(shown), "proxy"
                    piece = self._crop_of_display(shown)
                    if piece is not None:
                        return piece, "proxy"
            full, crop, landed = self.hunt_fetcher.keyframe(idx)
            self.cache.put(landed, crop)  # free bytes are never refused
            self.admitted_free += 1
            if full_view:
                return self._with_rect(full), f"kf Δ{idx - landed}"
            return crop, f"kf Δ{idx - landed}"  # exact crop pixels
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
                piece = self._crop_of_display(lo)
                if piece is not None:
                    return piece, "lo"
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
                image, field_ms, paint_ms = self._with_tool(target, image, task)
                self._show(image)
                run.log(task, target, route, ms,
                        field_ms=field_ms, paint_ms=paint_ms)
                self._recent.append(ms)
                self._last_serve_ms = ms
                self._last_field_ms = field_ms
                self._last_paint_ms = paint_ms
                if field_ms:
                    self._field_recent.append(field_ms)
                if paint_ms:
                    self._paint_recent.append(paint_ms)
                mean = sum(self._recent) / len(self._recent)
                # three clocks, never one total: a conflated number is how
                # a slow overlay reads as a slow store, and that mistake
                # has already cost this tree a day
                self.hud.setText(
                    f"frame {target:>6} · {task:<5} · {route:<9}"
                    f" · serve {ms:6.1f} · field {field_ms:5.1f}"
                    f" · paint {paint_ms:5.1f} ms · serve mean "
                    f"{mean:6.1f} ms")
                self.slider.blockSignals(True)
                self.slider.setValue(target)
                self.slider.blockSignals(False)
                QApplication.processEvents()
        finally:
            self._busy = False
            self._touch()

    def _with_tool(self, row: int, image: np.ndarray, task: str):
        """Compute the field, keep its number, draw it. Three clocks.

        This is where the byproduct claim is settled. The frame is already
        served and hot; computing the field to draw it produces exactly the
        number a sweep would have written, so the series is written here
        and the sweep only ever owes the ground nobody looked at.

        It runs only inside a window, where the cache already holds frames
        in the tool's own form. Out in the hunt the served pixels are proxy
        or keyframe pixels — a different form, and an approximate one, so a
        field computed on them would be a number about a different picture.
        `forms.py` refuses to record those, and so does this.
        """
        if not self.overlay_btn.isChecked() or not self._in_window(row):
            return image, 0.0, 0.0
        tool = self.rig.tool
        want = tool.needs(row)
        frames = {r: self.cache.get(r) for r in want}
        missing = [r for r in want if frames[r] is None]
        if missing:
            # a miss the declaration predicted is the bug this counter
            # exists to name; one it could not have is just a hop
            for r in missing:
                if r in self.rig.declared:
                    self.rig.avoidable += 1
                else:
                    self.rig.unavoidable += 1
            return image, 0.0, 0.0
        before = time.perf_counter()
        got = self.rig.evaluate(row, frames)
        field_ms = (time.perf_counter() - before) * 1000
        if got is None:
            return image, field_ms, 0.0
        field, value = got
        crop = tuple(CROP_RECT)
        row_series = self.rig.series_for(crop)
        if row_series.get(row) is None:
            self.rig.by_watching += 1
        row_series.put(row, value)
        ceiling = self.rig.ceiling_for(crop)
        if not ceiling:
            ceiling = self.rig.ceiling_for(crop, max(float(field.max()), 1.0))
            self.ceiling_spin.blockSignals(True)
            self.ceiling_spin.setValue(int(min(255, round(ceiling))))
            self.ceiling_spin.blockSignals(False)
        before = time.perf_counter()
        painted = surfaces.overlay(image, field, ceiling)
        paint_ms = (time.perf_counter() - before) * 1000
        # the horizon the transport implies: a run ahead while playing, the
        # point itself while paused or hopping. Recorded so the next miss
        # can say whether it was predictable.
        ahead = 12 if self._play_timer.isActive() and not self.hop_btn.isChecked() else 1
        self.rig.declared = self.rig.horizon(row, ahead)
        return painted, field_ms, paint_ms

    def _repaint_current(self) -> None:
        """Re-serve where we stand, so a display change is visible at once.

        A re-serve rather than a re-paint of the held pixmap: the overlay
        needs the field, the field needs the frames, and the served frame
        is the only thing that knows which form they are in.
        """
        if getattr(self, "_last_image", None) is not None:
            self.request(self.pos, "step")

    def _tool_picked(self, name: str) -> None:
        self.rig.use(name)
        self.ceiling_spin.blockSignals(True)
        self.ceiling_spin.setValue(
            int(min(255, round(self.rig.ceiling_for(tuple(CROP_RECT))))))
        self.ceiling_spin.blockSignals(False)
        self._mark("tool", name)
        self.hud.setText(
            f"tool: {name} — offsets {self.rig.tool.offsets}, reach "
            f"{self.rig.tool.reach}. The other tool's series is not cleared; "
            "it is a different key and comes back when you switch back.")
        self._render_series()
        self._repaint_current()

    def _ceiling_changed(self, value: int) -> None:
        self.rig.ceiling_for(tuple(CROP_RECT), float(value))
        self._repaint_current()

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
            lines.append(f"SWEEP {self._flow_value} {elapsed:.1f}s")
        elif self._debounce.isActive():
            lines.append("SIGNAL settling...")
        if self.builder is not None and self.builder.proc is not None:
            at = self.builder.batch[0] if self.builder.batch else 0
            lines.append(f"PROXY BUILD {self._seg_have}/{self._seg_expected}"
                         f" batch@{at}")
        if self.strip.computed < self.total - 1:
            lines.append(
                f"SIGNAL STRIP {100 * self.strip.computed // self.total}%")
        return lines

    def _show(self, image: np.ndarray) -> None:
        if not image.flags.c_contiguous:
            image = np.ascontiguousarray(image)
        self._last_image = image
        lines = self._overlay_lines()
        # on a fixed camera every frame looks the same, so position must
        # be its own feedback channel: a timecode, large while scrubbing
        # (measured: drags repaint at ~90 Hz and read as frozen anyway)
        secs = self.pos / self.fps
        tc = f"{int(secs // 60)}:{secs % 60:04.1f}  f{self.pos}"
        image = image.copy()
        fs = max(0.5, image.shape[1] / 1800)
        tc_fs = fs * (2.6 if self._scrubbing else 1.0)
        (tw, th), _ = cv2.getTextSize(tc, cv2.FONT_HERSHEY_SIMPLEX,
                                      tc_fs, max(1, round(1.5 * tc_fs)))
        org = (image.shape[1] - tw - round(12 * fs), th + round(10 * fs))
        cv2.putText(image, tc, org, cv2.FONT_HERSHEY_SIMPLEX, tc_fs,
                    0, max(2, round(4 * tc_fs)), cv2.LINE_AA)
        cv2.putText(image, tc, org, cv2.FONT_HERSHEY_SIMPLEX, tc_fs,
                    255, max(1, round(1.5 * tc_fs)), cv2.LINE_AA)
        if lines:
            pitch = round(34 * fs)
            for i, text in enumerate(lines):
                org = (round(12 * fs), pitch * (i + 1))
                cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                            fs, 0, max(2, round(4 * fs)), cv2.LINE_AA)
                cv2.putText(image, text, org, cv2.FONT_HERSHEY_SIMPLEX,
                            fs, 255, max(1, round(1.5 * fs)), cv2.LINE_AA)
        # the overlay makes the served frame three-channel; without it the
        # loop stays in luma all the way to the screen, which is a copy
        # per displayed frame not taken
        if image.ndim == 3:
            h, w = image.shape[:2]
            image = np.ascontiguousarray(image[:, :, ::-1])  # BGR -> RGB
            qimage = QImage(image.data, w, h, image.strides[0],
                            QImage.Format.Format_RGB888)
        else:
            h, w = image.shape
            qimage = QImage(image.data, w, h, image.strides[0],
                            QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage).scaled(
            self.canvas.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation)
        self._pix_w, self._pix_h = pixmap.width(), pixmap.height()
        self.canvas.setPixmap(pixmap)
        # paint NOW, synchronously: during a drag the app never returns to
        # the main event loop (each processEvents pulls the next mouse
        # move, which re-enters request), so the deferred paint starves —
        # measured 198 serves, zero paints across a 3 s drag storm. The
        # frozen-drag report was real and the earlier probe measured
        # setPixmap calls, not pixels.
        self.canvas.repaint()
        # the strip is the timeline now, so its playhead must move at
        # gesture rate, not at the 2 Hz status tick
        now = time.perf_counter()
        if now - getattr(self, "_strip_drawn", 0.0) > 0.05:
            self._strip_drawn = now
            self._render_strip()
            self.strip_label.repaint()

    # ── windows ──────────────────────────────────────────────────────────
    def _strip_pressed(self, frac: float) -> None:
        self._scrub_began()
        self.slider.setValue(self._frame_of(frac))

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
            self.hud.setText("drawing a crop needs the whole frame — check "
                             "'full frame', then drag the rectangle")
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
        """The tool's own parameter, debounced.

        Deliberately *not* the old signal knob. This one sits above the
        invalidation line: it changes the field, so it names a different
        series, and the frames it is computed from are untouched. Compare
        it against redrawing the crop, which is a form change and takes the
        frames with it. If both feel the same, the line is wrong.
        """
        self.signal_label.setText(f"blur={value - 1}")
        self._debounce.start()

    def _param_fire(self) -> None:
        blur = self.signal_slider.value() - 1
        if blur == self.rig.blur:
            return
        before = time.perf_counter()
        self.rig.use(blur=blur)
        s = self.rig.series_for(tuple(CROP_RECT))
        self._mark("param", f"blur={blur}")
        self._render_series()
        self._render_strip()
        self._repaint_current()
        wall = (time.perf_counter() - before) * 1000
        self.hud.setText(
            f"blur={blur}: a different series ({self.rig.tool.key()}), "
            f"{s.coverage(0, self.total) * 100:.1f}% covered, in "
            f"{wall:.0f} ms — the frames never moved. Redraw the crop to "
            "feel what a form change costs instead.")

    def _work_broke(self, err: str) -> None:
        self._flow_busy = False
        self._sweep_busy = False
        self._act_end(getattr(self, "_sweep_act", None), "failed")
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

            # leg 3: tune — the two halves of the invalidation line, in
            # order, so a reader of the log can subtract them: a parameter
            # change names a different series and leaves the frames alone,
            # then a sweep re-pays that series while the fill yields
            self._announce("[walk] tuning: parameter twice (series only), "
                           "then a sweep preempting fill")
            self.preempt.setChecked(True)
            for v in (4, 2):
                self.signal_slider.setValue(v)
                self._walk_wait_flow()
            self._sweep(whole=False)
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
        self._render_strip()
        # keep overlays current while nothing is being requested — a flow
        # or encode finishing must vanish from the frame without a scrub
        # (strip render above is a few ms of numpy at 2 Hz)
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
        # the tool line: what it is, what it holds, what it has covered,
        # and the one number that says whether the declaration is working.
        # An avoidable decode is invisible without this — it looks exactly
        # like the store being slow, which is the mistake that cost a day.
        rig = self.rig
        held = len(rig.declared)
        s = rig.series_for(tuple(CROP_RECT))
        field_mean = (sum(self._field_recent) / len(self._field_recent)
                      if self._field_recent else 0.0)
        paint_mean = (sum(self._paint_recent) / len(self._paint_recent)
                      if self._paint_recent else 0.0)
        self.status.setText(
            f"{self._config_for(self.pos)}   |   {rig.tool.key()} "
            f"offsets={rig.tool.offsets} declared={held}  "
            f"field {field_mean:.1f} / paint {paint_mean:.1f} ms  "
            f"series {s.coverage(0, self.total) * 100:.1f}% "
            f"(watching {rig.by_watching}, sweep {rig.by_sweep})  "
            f"avoidable decodes {rig.avoidable} "
            f"(unpredictable {rig.unavoidable})")

    def _render_strip(self) -> None:
        w_px = self.strip_label.width()
        if w_px < 20:
            return
        with self.strip.lock:
            e = self.strip.energy.copy()
        H = max(24, self.strip_label.height())
        # two bands, sized before anything is drawn: motion energy on top,
        # the tool's series under it. The series band is where coverage
        # growing behind the playhead is something you watch rather than
        # something the log tells you afterwards.
        band_h = min(30, H // 3)
        top_h = H - band_h - 2
        cols = (np.arange(self.total) * w_px // self.total).astype(np.int64)
        filled = np.where(np.isnan(e), -1.0, e).astype(np.float32)
        colmax = np.full(w_px, -1.0, dtype=np.float32)
        np.maximum.at(colmax, cols, filled)
        known = colmax >= 0
        img = np.full((H, w_px, 3), 18, dtype=np.uint8)
        if known.any():
            valid = e[~np.isnan(e)]
            lo = float(np.percentile(valid, 50))   # the noise baseline —
            hi = float(np.percentile(valid, 99.5))  # quiet sits low,
            span = max(hi - lo, 1e-6)               # bouts pop
            h = np.zeros(w_px, dtype=np.int64)
            h[known] = (np.clip((colmax[known] - lo) / span, 0, 1)
                        * (top_h - 5) + 1).astype(np.int64)
            bars = np.arange(top_h)[:, None] >= (top_h - h[None, :])
            img[:top_h][bars & known[None, :]] = (74, 205, 94)
        img[top_h - 3:top_h, ~known] = 62   # unknown ground: a dim baseline
        band = self._series_band(w_px, band_h)
        if band is not None:
            img[H - band_h:] = band
        if self.active is not None:
            c0 = self.active[0] * w_px // self.total
            c1 = max(c0 + 2, self.active[1] * w_px // self.total)
            img[0:3, c0:c1] = (86, 148, 255)
        pc = self.pos * w_px // self.total
        img[:, pc : pc + 2] = 235
        qimage = QImage(np.ascontiguousarray(img).data, w_px, H, 3 * w_px,
                        QImage.Format.Format_RGB888)
        self.strip_label.setPixmap(QPixmap.fromImage(qimage.copy()))

    def _series_band(self, w_px: int, height: int):
        """The whole timeline's series as one column per pixel.

        `to_columns` does the reducing — min/max per column rather than a
        mean, because a one-frame spike averaged with its neighbours never
        reaches the screen and events are the point. Coverage is drawn as
        its own ink instead of being folded into the value: a column with
        nothing computed and a column that really is zero must not look
        alike, which is coverage-inferred-from-a-zero at display.
        """
        if w_px < 20 or height < 6:
            return None
        s = self.rig.series_for(tuple(CROP_RECT))
        cols = surfaces.to_columns(s.values, s.covered, w_px)
        seen = cols["covered"] > 0
        band = np.full((height, w_px, 3), 12, dtype=np.uint8)
        if not seen.any():
            band[height - 1, :] = (46, 46, 46)
            return band
        top = float(cols["max"][seen].max()) or 1.0
        lo = np.clip(cols["min"] / top, 0, 1)
        hi = np.clip(cols["max"] / top, 0, 1)
        y0 = (height - 1 - hi * (height - 2)).astype(np.int64)
        y1 = (height - 1 - lo * (height - 2)).astype(np.int64)
        rows = np.arange(height)[:, None]
        span = (rows >= y0[None, :]) & (rows <= y1[None, :]) & seen[None, :]
        band[span] = (196, 132, 232)
        partial = seen & (cols["covered"] < 1)
        band[height - 1, seen] = (120, 90, 150)
        band[height - 1, partial] = (150, 120, 60)   # some rows, not all
        band[height - 1, ~seen] = (46, 46, 46)       # nothing computed here
        return band

    def _render_series(self) -> None:
        """The active window's series, drawn the same way at window scale."""
        w_px = max(20, self.series_label.width())
        h_px = max(40, self.series_label.height())
        s = self.rig.series_for(tuple(CROP_RECT))
        start, end = self.active if self.active else (0, self.total)
        values, covered = s.values[start:end], s.covered[start:end]
        cols = surfaces.to_columns(values, covered, w_px)
        img = np.full((h_px, w_px, 3), 18, dtype=np.uint8)
        seen = cols["covered"] > 0
        if seen.any():
            top = float(cols["max"][seen].max()) or 1.0
            lo = np.clip(cols["min"] / top, 0, 1)
            hi = np.clip(cols["max"] / top, 0, 1)
            y0 = (h_px - 2 - hi * (h_px - 12)).astype(np.int64)
            y1 = (h_px - 2 - lo * (h_px - 12)).astype(np.int64)
            rows = np.arange(h_px)[:, None]
            band = (rows >= y0[None, :]) & (rows <= y1[None, :]) & seen[None, :]
            img[band] = (196, 132, 232)
        img[h_px - 2:, ~seen] = (64, 44, 44)
        if self.active and self.active[0] <= self.pos < self.active[1]:
            pc = int((self.pos - start) / max(1, end - start) * (w_px - 1))
            img[:, pc:pc + 2] = 235
        text = (f"{self.rig.name}  {int(seen.sum())}/{w_px} cols  "
                f"{s.coverage(start, end) * 100:.0f}% of window")
        cv2.putText(img, text, (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42,
                    (170, 170, 170), 1, cv2.LINE_AA)
        qimage = QImage(np.ascontiguousarray(img).data, w_px, h_px,
                        3 * w_px, QImage.Format.Format_RGB888)
        self.series_label.setPixmap(QPixmap.fromImage(qimage.copy()))

    def _sweep(self, whole: bool) -> None:
        """Compute the tool over a span, on the user's say.

        A button rather than a background default. The user asked for it,
        so it is allowed to make the loop worse; what it is not allowed to
        do is keep doing so once they go back to tuning, which is what the
        stop flag and the yield between chunks are for.
        """
        if self._sweep_busy:
            self._sweep_stop.set()
            self.hud.setText("sweep: stopping")
            return
        span = (0, self.total) if whole else self.active
        if span is None:
            self.hud.setText("sweep: land a window first, or sweep all")
            return
        tool, crop = self.rig.tool, tuple(CROP_RECT)
        s = self.rig.series_for(crop)
        self._sweep_stop.clear()
        self._sweep_busy = True
        # the sweep inherits what the flow re-pay used to be: the same
        # ledger row, the same live overlay line, and the same priority
        # inversion. A run the user launched may take the frontier's decode
        # bandwidth; what it may not do is hold it after they come back.
        preempt = self.preempt.isChecked()
        if preempt and self.fill and self.fill.running():
            self.fill.pause.set()
        self._flow_busy = True
        self._flow_started = self._now()
        self._flow_value = f"{self.rig.name} {span[0]}-{span[1]}"
        act = self._act_start(
            "sweep", f"{self.rig.tool.key()} {span[0]}-{span[1]}"
                     f"{' preempting fill' if preempt else ''}")

        def worker():
            written = 0
            try:
                fetcher = Fetcher()
                start, end = span
                # only the gaps: a sweep owes the ground nobody looked at,
                # and everything the overlay already wrote is already right
                for gap_start, gap_end in s.missing(start, end):
                    if self._sweep_stop.is_set():
                        break
                    first = max(start, gap_start - tool.reach)
                    window: dict[int, np.ndarray] = {}
                    for row in range(first, gap_end):
                        if self._sweep_stop.is_set():
                            break
                        got = self.cache.get(row)
                        if got is None:
                            got = fetcher.exact(row)
                        window[row] = got
                        for old in [r for r in window if r < row - tool.reach]:
                            window.pop(old)
                        if row < gap_start:
                            continue        # still filling the warm-up
                        out = self.rig.evaluate(row, window)
                        if out is not None:
                            s.put(row, out[1])
                            written += 1
                        if written % SWEEP_CHUNK == 0:
                            time.sleep(0.002)   # let the GUI thread breathe
                fetcher.close()
            except Exception as exc:  # noqa: BLE001
                self.work_failed.emit(f"sweep: {exc!r}"[:200])
                return
            self.sweep_done.emit(written)

        threading.Thread(target=worker, daemon=True).start()
        self._sweep_act = act

    def _sweep_landed(self, written: int) -> None:
        self._sweep_busy = False
        self._flow_busy = False
        if self.fill:
            self.fill.pause.clear()
        self.rig.by_sweep += written
        self._act_end(getattr(self, "_sweep_act", None), f"wrote {written}")
        config = self._config_for(self.active[0]) if self.active else None
        if config in self.runs:
            self.runs[config].walls.append({
                "what": "sweep", "wall_s": round(self._now() - self._flow_started, 2),
                "detail": f"{self.rig.tool.key()} wrote {written} rows, "
                          f"preempt={'on' if self.preempt.isChecked() else 'off'}"})
        crop = tuple(CROP_RECT)
        s = self.rig.series_for(crop)
        self.hud.setText(
            f"sweep wrote {written} rows; {self.rig.by_watching} of this "
            f"series came from watching, {self.rig.by_sweep} from sweeps "
            f"({s.coverage(0, self.total) * 100:.1f}% of the timeline)")
        self._render_series()
        self._render_strip()
        self._touch()

    def _touch(self) -> None:
        # the live surfaces are cheap enough to refresh on every serve;
        # the matplotlib figure is not, and is on a button instead of a
        # timer for exactly that reason
        self._render_series()
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
            "tool": {
                "name": self.rig.name, "key": self.rig.tool.key(),
                "offsets": list(self.rig.tool.offsets),
                "reach": self.rig.tool.reach,
                "form": self.rig.form(tuple(CROP_RECT)).key(),
                "sequential": self.rig.tool.sequential,
            },
            "avoidable_decodes": self.rig.avoidable,
            "unavoidable_decodes": self.rig.unavoidable,
            "series_rows_by_watching": self.rig.by_watching,
            "series_rows_by_sweep": self.rig.by_sweep,
            "series": [
                {"key": key, "covered": int(v.covered.sum()),
                 "rows": int(len(v.covered))}
                for key, v in self.rig.series.items()
            ],
            "pts_index": {"packets": self._packets_seen,
                          "rows": self.total,
                          "build_s": round(self._index_s, 3),
                          "timebase": self.timebase},
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
        self.strip.stop()
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
        # the tool half: overlay writes the series by drawing, a sweep
        # covers what nobody looked at, and a parameter change names a
        # different series without touching a frame
        for name in TOOLS:
            window.tool_box.setCurrentText(name)
            window.request(4020, "step")
            rig = window.rig
            covered = rig.series_for(tuple(CROP_RECT)).coverage(4000, 4300)
            print(f"  {name:<22} key={rig.tool.key():<28} "
                  f"field={window._last_field_ms:6.2f} "
                  f"paint={window._last_paint_ms:6.2f} ms "
                  f"watched={rig.by_watching} covered={covered * 100:.1f}%")
        window.tool_box.setCurrentText("absdiff")
        before = window.rig.series_for(tuple(CROP_RECT)).coverage(4000, 4300)
        window._sweep(whole=False)
        window._walk_wait_flow()
        after = window.rig.series_for(tuple(CROP_RECT)).coverage(4000, 4300)
        print(f"sweep: window coverage {before * 100:.1f}% -> {after * 100:.1f}%"
              f"  (watching {window.rig.by_watching}, sweep {window.rig.by_sweep})")
        window.signal_slider.setValue(4)      # a parameter, not a form
        window._walk_wait_flow()
        window._param_fire()
        print(window.hud.text())
        print(f"series held: {list(window.rig.series)}")
        print(f"avoidable decodes {window.rig.avoidable}, "
              f"unpredictable {window.rig.unavoidable}")
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
