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
              anywhere on the timeline) lands a 300-frame window centered
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
    QSlider,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE  # noqa: E402

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
PROXY = FOOTAGE / "derived" / "proxy-1328-intra.mp4"
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
                "proxy": "#17becf", "kf": "#ff9310", "miss": "#d62728"}
ACT_ROWS = {"fill": 0, "encode": 1, "flow": 2}
ACT_COLORS = {"fill": "#1f77b4", "encode": "#909090", "flow": "#c218c2"}


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
            for pkt in stream.encode():
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

    def __init__(self, start: int, end: int, cache: Store, store: ChunkStore,
                 encode_q: queue.Queue, on_covered):
        self.start, self.end = start, end
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

    def stop(self) -> None:
        self._stop.set()
        self.pause.clear()
        if self._thread:
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
        try:
            for cstart in range(self.start, self.end, CHUNK_FRAMES):
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

    def log(self, task: str, frame: int, route: str, ms: float) -> None:
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

    def __init__(self):
        super().__init__()
        self.covered.connect(self._window_covered)
        self.flow_done.connect(self._flow_landed)
        self.work_failed.connect(self._work_broke)
        self.setWindowTitle("session explorer — hunt, land, tune, jump")
        self.resize(1680, 900)
        with av.open(str(BIG)) as c:
            stream = c.streams.video[0]
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
        self.cache = Store(600)
        self.store = ChunkStore()
        self.miss_fetcher = Fetcher()
        self.hunt_fetcher = Fetcher()
        self.proxy = ProxyFetcher() if PROXY.exists() else None
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
        self._playing = self._looping = self._hopping = False
        self._scrub_timer = QTimer(self)
        self._scrub_timer.timeout.connect(self._scrub_tick)
        self._scrub_targets: list[int] = []
        self._debounce = QTimer(self, singleShot=True, interval=DEBOUNCE_MS)
        self._debounce.timeout.connect(self._flow_fire)
        LOGS.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS / f"session-explorer-{stamp}.json"
        self._graph_timer = QTimer(self, singleShot=True, interval=600)
        self._graph_timer.timeout.connect(self._redraw_graphs)
        self._save_timer = QTimer(self, singleShot=True, interval=2500)
        self._save_timer.timeout.connect(self._save_log)
        self._hud_timer = QTimer(self, interval=500)
        self._hud_timer.timeout.connect(self._refresh_status)
        self._hud_timer.start()

        self.hunt_box = QComboBox()
        self.hunt_box.addItems(["hunt: proxy", "hunt: kf-snap"])
        if self.proxy is None:
            self.hunt_box.setCurrentIndex(1)
            self.hunt_box.setEnabled(False)
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
        self.loop_btn = QPushButton("loop window")
        self.loop_btn.setCheckable(True)
        self.loop_btn.setToolTip("loop playback inside the active window — "
                                 "the tuning gesture")
        self.loop_btn.toggled.connect(self._toggle_loop)
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
        for w in (self.play_btn, self.loop_btn, self.hop_btn,
                  self.scrub_btn, self.walk_btn):
            row2.addWidget(w)
        top = QVBoxLayout()
        top.addLayout(row1)
        top.addLayout(row2)

        self._view = "full"     #: what the canvas shows: full frame or crop
        self._pix_w = self._pix_h = 0
        self.canvas = CropCanvas()
        self.canvas.setMinimumSize(280, 180)
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
        self.slider.sliderPressed.connect(
            lambda: self.loop_btn.setChecked(False))
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

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addLayout(top)
        left_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(self.slider)
        left_layout.addWidget(self.coverage)
        left_layout.addWidget(self.hud)
        left_layout.addWidget(self.status)

        self.trace_fig = Figure(layout="constrained")
        self.trace_canvas = FigureCanvasQTAgg(self.trace_fig)
        self.stats = QPlainTextEdit(readOnly=True)
        self.stats.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 9pt;")
        save_lbl = QLabel(f"log: {self.log_path.name}")
        save_lbl.setStyleSheet("color: #888; font-size: 8pt;")
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.trace_canvas, 3)
        right_layout.addWidget(self.stats, 2)
        right_layout.addWidget(save_lbl)
        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([760, 920])
        self.setCentralWidget(splitter)
        self.request(0, "open")

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

    def _serve(self, idx: int, task: str, exact: bool) -> tuple[np.ndarray, str]:
        if not self._in_window(idx):
            self._view = "full"
            if self.hunt_box.currentIndex() == 0 and self.proxy is not None:
                return self._with_rect(self.proxy.frame(idx)), "proxy"
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
            near = self.cache.nearest(idx)
            if near is not None:
                best, arr = near
                return arr, f"near Δ{idx - best}"
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
        tuning scrub and the loop resumes; release anywhere else commits
        attention there, so a window lands and the loop starts."""
        value = self.slider.value()
        if self._in_window(value):
            self.request(value, "drag", exact=True)
            self.loop_btn.setChecked(True)
            return
        self.request(value, "drag", exact=True)
        self._land_at(value)

    def _land_at(self, pos: int) -> None:
        self._set_window(pos - WINDOW // 2)
        self.loop_btn.setChecked(True)

    def _set_window(self, at: int) -> None:
        start = max(0, min(at, self.total - WINDOW))
        start -= start % CHUNK_FRAMES
        end = min(start + WINDOW, self.total)
        if self.active == (start, end):
            return
        if self.fill:
            self.fill.stop()
            self._act_end(self._fill_act, "stopped: window switched")
        self.active = (start, end)
        self._mark("window", f"@{start}")
        if start not in self.windows:
            self.windows.append(start)
            secs = start / self.fps
            self.window_box.addItem(f"window @{start} ({secs:.0f}s)")
        run = self._run_for(start)
        overlap = self._encoding_now[0]
        run.walls.append({
            "what": "window-open", "wall_s": 0.0,
            "detail": f"chunks-still-encoding={overlap}"})
        self.fill = WindowFill(
            start, end, self.cache, self.store, self._encode_q,
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
        self.loop_btn.setChecked(False)
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
            "click the timeline to land a window on the new crop")
        self.request(self.pos, "step")

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
    def _toggle_play(self, on: bool) -> None:
        if on:
            self._playing, self._looping, self._hopping = True, False, False
            self.loop_btn.setChecked(False)
            self.hop_btn.setChecked(False)
        else:
            self._playing = False
        self._drive()

    def _toggle_loop(self, on: bool) -> None:
        if on:
            self._playing, self._looping, self._hopping = False, True, False
            self.play_btn.setChecked(False)
            self.hop_btn.setChecked(False)
        else:
            self._looping = False
        self._drive()

    def _toggle_hop(self, on: bool) -> None:
        if on:
            self._playing, self._looping, self._hopping = False, False, True
            self.play_btn.setChecked(False)
            self.loop_btn.setChecked(False)
        else:
            self._hopping = False
        self._drive()

    def _drive(self) -> None:
        if self._playing or self._looping or self._hopping:
            # the loop is the product gesture, so it runs at video rate;
            # play and hop stay free-run to feel throughput
            interval = max(1, round(1000 / self.fps)) if self._looping else 0
            self._play_timer.start(interval)
        else:
            self._play_timer.stop()

    def _play_tick(self) -> None:
        if self._busy:
            return
        if self._hopping:
            if self.active is None:
                self.hop_btn.setChecked(False)
                return
            self.request(self._rng.randrange(*self.active), "hop")
            return
        if self._looping:
            if self.active is None:
                self.loop_btn.setChecked(False)
                return
            nxt = self.pos + 1
            if not self._in_window(nxt):
                nxt = self.active[0]
            self.request(nxt, "play")
            return
        nxt = self.pos + 1
        if nxt >= self.total:
            self.play_btn.setChecked(False)
            return
        self.request(nxt, "play")

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
            self._save_log()
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
        self.hud.setText("cold again: the whole timeline, no windows — hunt")
        self._touch()

    def _refresh_status(self) -> None:
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

    @staticmethod
    def _route_key(route: str) -> str:
        return route.split(" ")[0].split("Δ")[0]

    def _redraw_graphs(self) -> None:
        # the loop is the default state now, so graphs must update under
        # it — throttled, one hiccup every few seconds instead of never
        if self._busy:
            self._graph_timer.start(1200)
            return
        if self._play_timer.isActive() \
                and time.perf_counter() - self._last_graph < 5.0:
            self._graph_timer.start(1200)
            return
        self._last_graph = time.perf_counter()
        runs = self._ordered_runs()
        events = [e for r in runs for e in r.events]
        with self.act_lock:
            activity = [dict(a) for a in self.activity]
        now = self._now()
        fig = self.trace_fig
        fig.clear()
        if not events:
            ax = fig.add_subplot(111)
            ax.set_axis_off()
            self.trace_canvas.draw_idle()
            return
        gs = fig.add_gridspec(3, 1, height_ratios=[3.2, 1.0, 2.2],
                              hspace=0.12)
        ax_lat = fig.add_subplot(gs[0])
        ax_act = fig.add_subplot(gs[1], sharex=ax_lat)
        ax_cmp = fig.add_subplot(gs[2])

        # panel 1: the session — every request in time, colored by route
        by_route: dict[str, tuple[list, list]] = {}
        for e in events:
            key = self._route_key(e["route"])
            by_route.setdefault(key, ([], []))
            by_route[key][0].append(e["t"])
            by_route[key][1].append(max(e["ms"], 0.005))
        for key, (xs, ys) in sorted(by_route.items()):
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
        self.trace_canvas.draw_idle()

        header = ["session by route:"]
        for key in order:
            ys = by_route[key][1]
            header.append(
                f"  {key:<6} n={len(ys):<5}"
                f" p50={float(np.median(ys)):>8.2f}"
                f"  p95={float(np.percentile(ys, 95)):>8.1f} ms")
        self.stats.setPlainText(
            "\n".join(header) + "\n\n"
            + "\n\n".join(r.stats_text() for r in runs))

    def _save_log(self) -> None:
        if self._busy:
            self._save_timer.start(1500)
            return
        with self.act_lock:
            activity = [dict(a) for a in self.activity]
        payload = {
            "tool": "session-explorer.py",
            "when": datetime.now(timezone.utc).isoformat(),
            "sieve_rev": harness._sieve_rev(),
            "machine": harness._machine(),
            "versions": harness._versions(),
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
        self.loop_btn.setChecked(False)
        self.hop_btn.setChecked(False)
        if self.fill:
            self.fill.stop()
        self._save_log()
        self.miss_fetcher.close()
        self.hunt_fetcher.close()
        if self.proxy:
            self.proxy.close()
        self.store.destroy()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Right:
            self.request(self.pos + 1, "step")
        elif key == Qt.Key.Key_Left:
            self.request(self.pos - 1, "step")
        elif key == Qt.Key.Key_Space:
            self.loop_btn.toggle() if self.active else self.play_btn.toggle()
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
        if fig_path:
            window.trace_fig.set_size_inches(13, 8)
            window.trace_fig.savefig(fig_path, dpi=110)
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
        window._save_log()
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
