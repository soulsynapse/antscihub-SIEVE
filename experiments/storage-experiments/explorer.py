"""Feel the storage stack by hand: scrub a region while fill, persist and play fight over it.

The decode explorer feels *files*; this feels the *tier stack* the storage
experiments measured. One region of the uncut original (exp05's 300-frame
crop), one RAM cache in front of it, and every knob 02–05 put numbers behind:

  fill        off / sequential / near-playhead, in GOP x1/2/4 chunks — 02
              measured sequential + big chunks winning and playhead-chasing
              losing; drag while fill runs and feel the misses thin out.
  budget      LRU capacity in frames, with play-bypass — 03 measured a
              play-through dropping return scrubs from 100% to ~40% hits
              when play inserts. Press "play thru", then return to where you
              were scrubbing, with bypass on and off.
  miss policy block (the honest 300 ms), kf-snap (the storyboard gesture),
              nearest-cached (instant but Δ frames wrong; the HUD says how
              wrong). Slider release always fetches exact.
  persist     encode the grown cut from the cache in-process (04: ~3.4 s,
              foreground untouched); after it lands, misses route to the cut
              at ~10 ms instead of the original's ~300. Shrink the budget
              afterwards and feel RAM evict down onto the disk tier.
  flow        re-pay decode-free DIS over the cached region — the analysis
              wall a flow-parameter slider would cost (05: linear, ~1.2 s
              for a cached 300-frame region).

Every request logs task, route and ms; runs are keyed by stack config;
graphs and stats accumulate per launch and autosave to explorer-logs/.
"walk params" drives the whole space unattended — miss policies cold, fill
orders and chunk sizes against the scripted scrub, the pollution story with
bypass off then on, and the fill→persist→evict→flow happy path — so a
launch can feel every measured verdict without hunting for it.

Run:
    uv run --group experiments python experiments/storage-experiments/explorer.py
"""

from __future__ import annotations

import json
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
from harness import FOOTAGE, quantiles  # noqa: E402

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
GROWN_CUT = FOOTAGE / "derived" / "_explorer-grown-cut.mp4"
LOGS = Path(__file__).resolve().parent / "explorer-logs"

SPAN = 300
SPANS = (300, 1500, 4500)   #: region sizes; the composite only shows its
                            #: shape at span scale, where fill takes long
                            #: enough for policy to matter
START_S = 60
CHUNK_FRAMES = 96           #: persist chunk (GOP x4 - results/02-*)
SKELETON_STRIDE = 24        #: one kept frame per GOP: nearest is then wrong
                            #: by at most half a stride, everywhere, forever
TELEPORT_DIST = 240         #: frontier relocates when attention commits
TELEPORT_COOLDOWN_S = 1.0   #: this far away (10 GOPs) for this long
CROP_W, CROP_H, CROP_X, CROP_Y = 1024, 1024, 2144, 982
GOP = 24                #: results/04-* (decode side): fixed on this footage
NEAR_RADIUS = 12        #: nearest-cached serves within this many frames
EVENT_CAP = 20_000
TASK_MARKERS = {"drag": "o", "play": ".", "rev": "v", "step": "^",
                "open": "s", "hop": "x", "scrub": "d", "thru": "."}


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _crop_luma(frame):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    return np.ascontiguousarray(arr[CROP_Y : CROP_Y + CROP_H,
                                    CROP_X : CROP_X + CROP_W])


STEP_WITHIN = 60  #: step forward instead of seeking within this many frames
                  #: (exp02: the crossover on the uncut source)


class Fetcher:
    """One open container on the original, fetching region-relative frames.

    Sequential requests step the decoder forward instead of seeking — without
    this, play through the miss path costs the random-access price per frame
    (the first headless walk measured 300 frames of 'play thru' at 88 s)."""

    def __init__(self, base_idx: int):
        self.container = av.open(str(BIG))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)
        self.base_idx = base_idx
        self._decoded = None
        self._pos: int | None = None  # rel index of the last decoded frame

    def exact(self, rel: int) -> np.ndarray:
        if self._decoded is not None and self._pos is not None:
            ahead = rel - self._pos
            if 0 < ahead <= STEP_WITHIN:
                try:
                    for _ in range(ahead):
                        frame = next(self._decoded)
                    self._pos = rel
                    return _crop_luma(frame)
                except StopIteration:
                    pass  # ran off the end; fall through to a real seek
        target = self.pts_of(self.base_idx + rel)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        for frame in self._decoded:
            if frame.pts is not None and frame.pts + half >= target:
                self._pos = rel
                return _crop_luma(frame)
        raise RuntimeError(f"off the end at rel {rel}")

    def keyframe(self, rel: int) -> tuple[np.ndarray, int]:
        """One decode, no roll-forward: the storyboard gesture."""
        target = self.pts_of(self.base_idx + rel)
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        frame = next(self._decoded)
        landed = round((frame.pts - (self.stream.start_time or 0))
                       / self.step) - self.base_idx
        self._pos = landed
        return _crop_luma(frame), landed

    def close(self) -> None:
        self.container.close()


class CutFetcher:
    """The grown cut, once persist has made it: intra, so seeks are cheap."""

    def __init__(self, path: Path):
        self.container = av.open(str(path))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)

    def exact(self, rel: int) -> np.ndarray:
        target = self.pts_of(rel)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        for frame in self.container.decode(self.stream):
            if frame.pts is not None and frame.pts + half >= target:
                plane = frame.planes[0]
                arr = np.frombuffer(plane, dtype=np.uint8)
                arr = arr[: frame.height * plane.line_size]
                arr = arr.reshape(frame.height, plane.line_size)
                return np.ascontiguousarray(arr[:, : frame.width])
        raise RuntimeError(f"cut off the end at rel {rel}")

    def close(self) -> None:
        self.container.close()


class RamTier:
    """Budget-capped LRU keyed by region-relative index. The lock is for the
    fill thread; every op under it is a dict touch, never a decode."""

    def __init__(self, budget: int):
        self.budget = budget
        self.d: OrderedDict[int, np.ndarray] = OrderedDict()
        self.lock = threading.Lock()

    def get(self, rel: int):
        with self.lock:
            if rel in self.d:
                self.d.move_to_end(rel)
                return self.d[rel]
        return None

    def nearest(self, rel: int):
        with self.lock:  # read the value under the lock too - the fill
            if not self.d:  # thread evicts between a peek and a fetch
                return None
            best = min(self.d, key=lambda k: abs(k - rel))
            if abs(best - rel) <= NEAR_RADIUS:
                return best, self.d[best]
        return None

    def snapshot(self) -> dict[int, np.ndarray]:
        with self.lock:
            return dict(self.d)

    def put(self, rel: int, arr: np.ndarray) -> None:
        with self.lock:
            self.d[rel] = arr
            self.d.move_to_end(rel)
            while len(self.d) > self.budget:
                self.d.popitem(last=False)

    def set_budget(self, budget: int) -> None:
        with self.lock:
            self.budget = budget
            while len(self.d) > budget:
                self.d.popitem(last=False)

    def __len__(self):
        return len(self.d)


CHUNK_DIR = FOOTAGE / "derived" / "_explorer-chunks"


class ChunkStore:
    """Persist-as-you-go: the grown cut as one intra file per 96-frame chunk.

    A single growing mp4 cannot take chunks out of order (the muxer wants
    monotone dts, and a teleporting frontier produces jumps), so the disk
    tier is chunked — which is also the shape a real store wants: a chunk is
    the unit of persistence, eviction and coverage, and 'which chunks exist'
    is an explicit record, never inferred from a gap."""

    def __init__(self):
        self._open: OrderedDict[int, CutFetcher] = OrderedDict()
        CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _path(start: int) -> Path:
        return CHUNK_DIR / f"chunk-{start:05d}.mp4"

    def persisted(self) -> set[int]:
        return {int(p.stem.split("-")[1]) for p in CHUNK_DIR.glob("chunk-*.mp4")}

    def encode(self, start: int, frames: list[np.ndarray]) -> None:
        path = self._path(start)
        with av.open(str(path), "w") as out:
            stream = out.add_stream("libx264", rate=24)
            stream.width, stream.height = CROP_W, CROP_H
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": "18", "preset": "veryfast", "g": "1"}
            for arr in frames:
                vf = av.VideoFrame.from_ndarray(arr, format="gray")
                vf = vf.reformat(format="yuv420p")
                for pkt in stream.encode(vf):
                    out.mux(pkt)
            for pkt in stream.encode():
                out.mux(pkt)

    def fetch(self, rel: int) -> np.ndarray | None:
        start = rel - rel % CHUNK_FRAMES
        if start not in self._open:
            path = self._path(start)
            if not path.exists():
                return None
            self._open[start] = CutFetcher(path)
            while len(self._open) > 3:  # a few open containers is plenty
                _, old = self._open.popitem(last=False)
                old.close()
        self._open.move_to_end(start)
        return self._open[start].exact(rel - start)

    def wipe(self) -> None:
        for fetcher in self._open.values():
            fetcher.close()
        self._open.clear()
        for path in CHUNK_DIR.glob("chunk-*.mp4"):
            path.unlink(missing_ok=True)


class FrontierFill:
    """The composite candidate: one sequential decode frontier that teleports
    when attention commits elsewhere, keeps a stride skeleton exempt from
    eviction, fills the dense RAM tier as it passes, and hands each completed
    chunk to a persist thread. Ordering stays sequential because on this
    footage a seek costs a GOP (docs/findings/2026.08.21-uncut-seek-*), so
    jumping around buys nothing — the frontier only ever jumps for the user.
    """

    def __init__(self, base_idx: int, cache: RamTier, skeleton: dict,
                 skel_lock: threading.Lock, store: ChunkStore):
        self.base_idx = base_idx
        self.cache = cache
        self.skeleton = skeleton
        self.skel_lock = skel_lock
        self.store = store
        self.filled: set[int] = set()
        self.persisted: set[int] = store.persisted()
        self.last_req = [0]
        self._teleport_to: list[int | None] = [None]
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._encoder: threading.Thread | None = None
        import queue

        self._q: queue.Queue = queue.Queue()
        self.frontier_pos = 0

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def teleport(self, rel: int) -> None:
        self._teleport_to[0] = rel - rel % CHUNK_FRAMES

    def start(self) -> None:
        self.stop()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._encoder = threading.Thread(target=self._encode_loop, daemon=True)
        self._thread.start()
        self._encoder.start()

    def stop(self) -> None:
        self._stop.set()
        for t in (self._thread, self._encoder):
            if t:
                t.join(timeout=15)
        self._thread = self._encoder = None

    def _encode_loop(self) -> None:
        while not self._stop.is_set() or not self._q.empty():
            try:
                start, frames = self._q.get(timeout=0.2)
            except Exception:  # noqa: BLE001 - empty queue, keep waiting
                continue
            try:
                self.store.encode(start, frames)
                self.persisted.add(start)
            except Exception:  # noqa: BLE001 - a failed chunk re-derives
                pass

    def _run(self) -> None:
        pending = [s for s in range(0, SPAN, CHUNK_FRAMES)
                   if s not in self.persisted]
        fetcher = Fetcher(self.base_idx)
        pts_of, step = fetcher.pts_of, fetcher.step
        half = step / 2
        try:
            while pending and not self._stop.is_set():
                jump = self._teleport_to[0]
                if jump is not None and jump in pending:
                    self._teleport_to[0] = None
                    pending.remove(jump)
                    start = jump
                else:
                    start = pending.pop(0)
                self.frontier_pos = start
                target = pts_of(self.base_idx + start)
                fetcher.container.seek(target, stream=fetcher.stream)
                buffer: list[np.ndarray] = []
                rel = start
                end = min(start + CHUNK_FRAMES, SPAN)
                for frame in fetcher.container.decode(fetcher.stream):
                    if frame.pts is None or frame.pts + half < target:
                        continue
                    arr = _crop_luma(frame)
                    buffer.append(arr)
                    self.cache.put(rel, arr)
                    if rel % SKELETON_STRIDE == 0:
                        with self.skel_lock:
                            self.skeleton[rel] = arr
                    self.filled.add(rel)
                    self.frontier_pos = rel
                    rel += 1
                    if rel >= end or self._stop.is_set():
                        break
                if len(buffer) == end - start and start not in self.persisted:
                    self._q.put((start, buffer))
        finally:
            fetcher.close()


class FillWorker:
    """02's winning shape, restartable: GOP-aligned chunks into the RAM tier."""

    def __init__(self, base_idx: int):
        self.base_idx = base_idx
        self.thread: threading.Thread | None = None
        self.stop_flag = threading.Event()
        self.filled: set[int] = set()
        self.last_req = [0]

    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self, cache: RamTier, order: str, chunk: int) -> None:
        self.stop()
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(
            target=self._run, args=(cache, order, chunk, self.stop_flag),
            daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=10)
        self.thread = None

    def _run(self, cache: RamTier, order: str, chunk: int,
             stop: threading.Event) -> None:
        fetcher = Fetcher(self.base_idx)
        pts_of, step = fetcher.pts_of, fetcher.step
        half = step / 2
        remaining = {s for s in range(0, SPAN, chunk)
                     if any(r not in self.filled
                            for r in range(s, min(s + chunk, SPAN)))}
        try:
            while remaining and not stop.is_set():
                if order == "near-playhead":
                    pick = min(remaining,
                               key=lambda s: abs(s - self.last_req[0]))
                else:
                    pick = min(remaining)
                remaining.discard(pick)
                target = pts_of(self.base_idx + pick)
                fetcher.container.seek(target, stream=fetcher.stream)
                rel = pick
                for frame in fetcher.container.decode(fetcher.stream):
                    if frame.pts is None or frame.pts + half < target:
                        continue
                    cache.put(rel, _crop_luma(frame))
                    self.filled.add(rel)
                    rel += 1
                    if rel >= min(pick + chunk, SPAN) or stop.is_set():
                        break
        finally:
            fetcher.close()


class RunLog:
    """Everything one stack config was asked to do this launch."""

    def __init__(self, config: str):
        self.config = config
        self.label = config
        self.started = datetime.now(timezone.utc).isoformat()
        self._t0 = time.perf_counter()
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
                    k: round(v, 2) for k, v in quantiles(samples).items()}}
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
        for w in self.walls[-3:]:
            lines.append(f"  {w['what']}: {w['wall_s']:.2f}s ({w['detail']})")
        return "\n".join(lines)


class StorageExplorer(QMainWindow):
    #: worker threads report through queued signals — a widget touched from a
    #: worker thread is the crash, not a style point
    persist_done = Signal(float)
    persist_failed = Signal(str)
    flow_done = Signal(float, int)

    def __init__(self):
        super().__init__()
        self.persist_done.connect(self._persist_landed)
        self.persist_failed.connect(self._persist_broke)
        self.flow_done.connect(self._flow_landed)
        self.setWindowTitle("storage explorer — feel the tier stack")
        self.resize(1680, 900)
        with av.open(str(BIG)) as c:
            stream = c.streams.video[0]
            self.fps = float(stream.average_rate)
            self.base_idx = int(START_S * stream.average_rate) + 1
        self.cache = RamTier(SPAN)
        self.fill = FillWorker(self.base_idx)
        self.miss_fetcher = Fetcher(self.base_idx)
        self.cut: CutFetcher | None = None
        self.skeleton: dict[int, np.ndarray] = {}
        self.skel_lock = threading.Lock()
        self.store = ChunkStore()
        self.frontier: FrontierFill | None = None
        self._recent_targets: deque[int] = deque(maxlen=5)
        self._last_teleport = 0.0
        self.pos = 0
        self.run: RunLog | None = None
        self.runs: dict[str, RunLog] = {}
        self._busy = False
        self._queue: deque[int] = deque()
        self._recent: deque[float] = deque(maxlen=30)
        self._rng = random.Random()
        self._dir, self._hop = 1, False
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._play_tick)
        self._scrub_timer = QTimer(self)
        self._scrub_timer.timeout.connect(self._scrub_tick)
        self._scrub_targets: list[int] = []
        LOGS.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS / f"storage-explorer-{stamp}.json"
        self._graph_timer = QTimer(self, singleShot=True, interval=600)
        self._graph_timer.timeout.connect(self._redraw_graphs)
        self._save_timer = QTimer(self, singleShot=True, interval=2500)
        self._save_timer.timeout.connect(self._save_log)
        self._hud_timer = QTimer(self, interval=500)
        self._hud_timer.timeout.connect(self._refresh_status)
        self._hud_timer.start()

        self.span_box = QComboBox()
        self.span_box.addItems([f"span {s}" for s in SPANS])
        self.span_box.setToolTip(
            "region size. The composite frontier only shows its shape at "
            "span scale, where fill takes long enough for policy to matter; "
            "changing span resets everything cold.")
        self.span_box.currentIndexChanged.connect(self._span_changed)
        self.fill_box = QComboBox()
        self.fill_box.addItems(["fill off", "fill sequential",
                                "fill near-playhead",
                                "fill frontier (composite)"])
        self.fill_box.setToolTip(
            "02 measured sequential beating near-playhead even under a "
            "lingering scrub — the miss path already memoizes attention, "
            "chasing it starves coverage (results/02-*). Feel it: turn fill "
            "on and drag while it races you.")
        self.fill_box.currentTextChanged.connect(self._fill_changed)
        self.chunk_box = QComboBox()
        self.chunk_box.addItems(["chunk GOPx1", "chunk GOPx2", "chunk GOPx4"])
        self.chunk_box.setCurrentIndex(2)
        self.chunk_box.setToolTip(
            "fill chunk size. 02: GOPx4 nearly halved misses and fill wall "
            "against x1 by paying fewer seeks.")
        self.chunk_box.currentTextChanged.connect(self._fill_changed)
        self.budget_spin = QSpinBox()
        self.budget_spin.setRange(10, SPAN)
        self.budget_spin.setValue(SPAN)
        self.budget_spin.setSuffix(" frames RAM")
        self.budget_spin.setToolTip(
            "RAM tier capacity. Shrink it after persisting and feel evicted "
            "frames served by the grown cut (~10 ms) instead of the "
            "original (~300 ms).")
        self.budget_spin.valueChanged.connect(
            lambda v: self.cache.set_budget(v))
        self.bypass = QCheckBox("play bypasses cache")
        self.bypass.setChecked(True)
        self.bypass.setToolTip(
            "03: with play inserting into a capped LRU, one play-through "
            "dropped return scrubs from 100% to ~40% hits. Uncheck, press "
            "'play thru', then go back to where you were scrubbing.")
        self.miss_box = QComboBox()
        self.miss_box.addItems(["miss: block", "miss: kf-snap",
                                "miss: nearest-cached"])
        self.miss_box.setToolTip(
            "what a cache miss does mid-drag. block = exact fetch from the "
            "original (~300 ms, honest); kf-snap = one decode at the GOP "
            "head (Δ up to half a GOP, HUD prints it); nearest-cached = "
            f"serve a cached frame within {NEAR_RADIUS} (instant, wrong by "
            "Δ). Slider release is always exact.")
        self.persist_btn = QPushButton("persist cut")
        self.persist_btn.setToolTip(
            "encode the grown cut from the RAM tier, in-process — 04: ~3.4 s "
            "for the region, foreground untouched. Needs full coverage; "
            "after it lands, misses route to the cut.")
        self.persist_btn.clicked.connect(self._persist)
        self.flow_btn = QPushButton("re-pay flow")
        self.flow_btn.setToolTip(
            "DIS-ultrafast + reduce over every cached frame in order — the "
            "wall a flow-parameter slider would cost (05: linear, ~1.2 s "
            "for a cached 300-frame region, 26 s at 3000 proxy frames).")
        self.flow_btn.clicked.connect(self._flow)
        self.reset_btn = QPushButton("reset cold")
        self.reset_btn.setToolTip(
            "drop the RAM tier, the grown cut and the fill worker — back to "
            "a cold open of the region.")
        self.reset_btn.clicked.connect(self._reset)

        self.play_btn = QPushButton("play")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self._toggle_play)
        self.rev_btn = QPushButton("play ◀")
        self.rev_btn.setCheckable(True)
        self.rev_btn.toggled.connect(self._toggle_rev)
        self.hop_btn = QPushButton("hop")
        self.hop_btn.setCheckable(True)
        self.hop_btn.setToolTip("uniform-random frames, free-run — sustained "
                                "random access through the stack")
        self.hop_btn.toggled.connect(self._toggle_hop)
        self.thru_btn = QPushButton("play thru")
        self.thru_btn.setToolTip(
            "one full pass over the region through the cache — the polluter "
            "from 03. With bypass off and a small budget it evicts exactly "
            "what you kept returning to.")
        self.thru_btn.clicked.connect(self._play_through)
        self.scrub_btn = QPushButton("scripted scrub")
        self.scrub_btn.setToolTip(
            "02's lingering scrub (gaussian around a jumping anchor) at "
            "20 Hz, 100 fetches — the same hands the harness used, so felt "
            "and measured sessions land in comparable logs.")
        self.scrub_btn.clicked.connect(self._scripted_scrub)
        self.walk_btn = QPushButton("walk params")
        self.walk_btn.setToolTip(
            "drive the whole parameter space while you watch: each miss "
            "policy cold, each fill order and chunk size against the "
            "scripted scrub, the pollution story with bypass off then on, "
            "then the happy path — fill to full, persist, shrink RAM, hop "
            "on the cut, re-pay flow. Every leg lands in the graphs and "
            "stats as its own config.")
        self.walk_btn.clicked.connect(self._walk)

        row1 = QHBoxLayout()
        for w in (self.span_box, self.fill_box, self.chunk_box,
                  self.budget_spin, self.bypass, self.miss_box):
            row1.addWidget(w)
        row1.addStretch(1)
        for w in (self.persist_btn, self.flow_btn, self.reset_btn):
            row1.addWidget(w)
        row2 = QHBoxLayout()
        row2.addStretch(1)
        for w in (self.play_btn, self.rev_btn, self.hop_btn, self.thru_btn,
                  self.scrub_btn, self.walk_btn):
            row2.addWidget(w)
        top = QVBoxLayout()
        top.addLayout(row1)
        top.addLayout(row2)

        self.canvas = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.canvas.setMinimumSize(280, 180)
        self.canvas.setStyleSheet("background: #101010;")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setMaximum(SPAN - 1)
        self.slider.sliderMoved.connect(lambda i: self.request(i, "drag"))
        self.slider.valueChanged.connect(lambda i: self.request(i, "drag"))
        self.slider.sliderReleased.connect(
            lambda: self.request(self.slider.value(), "drag", exact=True))
        self.coverage = QLabel("")
        self.coverage.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 8pt; color: #6a6;")
        self.hud = QLabel("cold: nothing cached, no cut, fill off")
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

        self.trace_fig = Figure(tight_layout=True)
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

    # ── config identity ──────────────────────────────────────────────────
    def _config(self) -> str:
        fill = self.fill_box.currentText().replace("fill ", "")
        chunk = self.chunk_box.currentText().replace("chunk ", "")
        miss = self.miss_box.currentText().replace("miss: ", "")
        parts = [f"span={SPAN}", f"fill={fill}", chunk, f"miss={miss}",
                 f"b={self.budget_spin.value()}"]
        if self.frontier:
            parts = [f"span={SPAN}", "COMPOSITE",
                     f"b={self.budget_spin.value()}"]
        if not self.bypass.isChecked():
            parts.append("play-fills")
        if self.cut:
            parts.append("cut")
        return " ".join(parts)

    def _current_run(self) -> RunLog:
        config = self._config()
        if config not in self.runs:
            self.runs[config] = RunLog(config)
        self.run = self.runs[config]
        return self.run

    def _fill_changed(self, _=None) -> None:
        order = self.fill_box.currentText().replace("fill ", "")
        if self.frontier:
            self.frontier.stop()
            self.frontier = None
        if order == "off":
            self.fill.stop()
            return
        if "frontier" in order:
            self.fill.stop()
            self.frontier = FrontierFill(self.base_idx, self.cache,
                                         self.skeleton, self.skel_lock,
                                         self.store)
            self.frontier.start()
            return
        chunk = GOP * (1, 2, 4)[self.chunk_box.currentIndex()]
        self.fill.start(self.cache, order, chunk)

    def _span_changed(self, _=None) -> None:
        global SPAN
        SPAN = SPANS[self.span_box.currentIndex()]
        self.budget_spin.setRange(10, SPAN)
        self.budget_spin.setValue(min(self.budget_spin.value(), SPAN))
        self.slider.setMaximum(SPAN - 1)
        self._reset()

    # ── the stack, one request at a time ─────────────────────────────────
    def _serve(self, rel: int, task: str, exact: bool) -> tuple[np.ndarray, str]:
        self.fill.last_req[0] = rel
        got = self.cache.get(rel)
        if got is not None:
            return got, "hit"
        if self.frontier:
            self.frontier.last_req[0] = rel
            with self.skel_lock:
                skel = self.skeleton.get(rel)
            if skel is not None:  # an exact frame the stride kept
                return skel, "skel"
            from_disk = self.store.fetch(rel)
            if from_disk is not None:
                self.cache.put(rel, from_disk)
                return from_disk, "cut"
            if not exact:  # bounded-Δ guarantee: dense ∪ skeleton
                near = self.cache.nearest(rel)
                if near is None:
                    with self.skel_lock:
                        best = min(self.skeleton,
                                   key=lambda k: abs(k - rel), default=None)
                        if best is not None and abs(best - rel) <= \
                                SKELETON_STRIDE // 2:
                            return self.skeleton[best], f"near Δ{rel - best}"
                else:
                    best, arr = near
                    return arr, f"near Δ{rel - best}"
            arr = self.miss_fetcher.exact(rel)
            self.cache.put(rel, arr)
            return arr, "miss"
        if self.cut:
            arr = self.cut.exact(rel)
            self.cache.put(rel, arr)
            return arr, "cut"
        policy = self.miss_box.currentText()
        if not exact and "kf-snap" in policy:
            arr, landed = self.miss_fetcher.keyframe(rel)
            if 0 <= landed < SPAN:  # a real decoded frame — keep it
                self.cache.put(landed, arr)
            return arr, f"kf Δ{rel - landed}"
        if not exact and "nearest" in policy:
            near = self.cache.nearest(rel)
            if near is not None:
                best, arr = near
                return arr, f"near Δ{rel - best}"
        arr = self.miss_fetcher.exact(rel)
        insert = not (task in ("play", "thru") and self.bypass.isChecked())
        if insert:
            self.cache.put(rel, arr)
        return arr, "miss"

    def request(self, rel: int, task: str = "step", exact: bool = False) -> None:
        rel = max(0, min(SPAN - 1, rel))
        if self.frontier and task in ("drag", "step", "scrub"):
            # committed-anchor teleport: five recent targets agreeing with
            # each other, all far from the frontier, and a cooldown — chasing
            # every request is the policy 02 measured losing
            self._recent_targets.append(rel)
            if len(self._recent_targets) == 5:
                lo, hi = min(self._recent_targets), max(self._recent_targets)
                center = (lo + hi) // 2
                now = time.perf_counter()
                if (hi - lo <= 60
                        and abs(center - self.frontier.frontier_pos)
                        > TELEPORT_DIST
                        and now - self._last_teleport > TELEPORT_COOLDOWN_S):
                    self.frontier.teleport(center)
                    self._last_teleport = now
        self._queue.clear()  # coalesce always: 02's foreground shape
        self._queue.append(rel)
        if self._busy:
            return
        self._busy = True
        try:
            while self._queue:
                target = self._queue.popleft()
                run = self._current_run()
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
                    f"frame {target:>4} · {task:<5} · {route:<9}"
                    f" · {ms:7.1f} ms · last {len(self._recent)} mean "
                    f"{mean:6.1f} ms")
                self.slider.blockSignals(True)
                self.slider.setValue(target)
                self.slider.blockSignals(False)
                QApplication.processEvents()
        finally:
            self._busy = False
            self._touch()

    def _show(self, image: np.ndarray) -> None:
        if not image.flags.c_contiguous:
            image = np.ascontiguousarray(image)
        h, w = image.shape
        qimage = QImage(image.data, w, h, image.strides[0],
                        QImage.Format.Format_Grayscale8)
        self.canvas.setPixmap(QPixmap.fromImage(qimage).scaled(
            self.canvas.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation))

    # ── tasks ────────────────────────────────────────────────────────────
    def _toggle_play(self, on: bool) -> None:
        if on:
            self._dir, self._hop = 1, False
            self.rev_btn.setChecked(False)
            self.hop_btn.setChecked(False)
        self._drive(on, self.play_btn, "play")

    def _toggle_rev(self, on: bool) -> None:
        if on:
            self._dir, self._hop = -1, False
            self.play_btn.setChecked(False)
            self.hop_btn.setChecked(False)
        self._drive(on, self.rev_btn, "play ◀")

    def _toggle_hop(self, on: bool) -> None:
        if on:
            self._hop = True
            self.play_btn.setChecked(False)
            self.rev_btn.setChecked(False)
        self._drive(on, self.hop_btn, "hop")

    def _drive(self, on: bool, btn: QPushButton, idle: str) -> None:
        if on:
            self._play_timer.start(0)
            btn.setText("pause")
            return
        btn.setText(idle)
        if not (self.play_btn.isChecked() or self.rev_btn.isChecked()
                or self.hop_btn.isChecked()):
            self._play_timer.stop()

    def _play_tick(self) -> None:
        if self._busy:
            return
        if self._hop:
            self.request(self._rng.randrange(SPAN), "hop")
            return
        nxt = self.pos + self._dir
        if nxt < 0 or nxt >= SPAN:
            self.play_btn.setChecked(False)
            self.rev_btn.setChecked(False)
            return
        self.request(nxt, "play" if self._dir > 0 else "rev")

    def _play_through(self) -> None:
        if self._busy:
            return
        self.hud.setText("play thru running…")
        self.hud.repaint()
        before = time.perf_counter()
        image = None
        for rel in range(SPAN):
            run = self._current_run()
            t0 = time.perf_counter()
            try:
                image, route = self._serve(rel, "thru", exact=True)
            except Exception as exc:  # noqa: BLE001 - one bad frame is a datum
                run.log("thru", rel, f"err {exc!r}"[:40], 0.0)
                continue
            run.log("thru", rel, route, (time.perf_counter() - t0) * 1000)
            if rel % 24 == 0:  # keep the window alive through a long pass
                self.slider.blockSignals(True)
                self.slider.setValue(rel)
                self.slider.blockSignals(False)
                QApplication.processEvents()
        wall = time.perf_counter() - before
        self.pos = SPAN - 1
        if image is not None:
            self._show(image)
        if self.run:
            self.run.walls.append(
                {"what": "play-thru", "wall_s": round(wall, 2),
                 "detail": f"bypass={'on' if self.bypass.isChecked() else 'off'}"})
        self.hud.setText(
            f"play thru: {SPAN} frames in {wall:.2f}s — now go back to where "
            "you were scrubbing")
        self._touch()

    def _scripted_scrub(self) -> None:
        rng = random.Random(7)
        targets, anchor = [], rng.randrange(SPAN)
        for _ in range(100):
            if rng.random() < 0.12:
                anchor = rng.randrange(SPAN)
            targets.append(max(0, min(SPAN - 1, round(rng.gauss(anchor, 8)))))
        self._scrub_targets = targets
        self._scrub_timer.start(50)

    def _scrub_tick(self) -> None:
        if not self._scrub_targets:
            self._scrub_timer.stop()
            self.hud.setText("scripted scrub done — stats compare configs")
            return
        if self._busy:
            return
        self.request(self._scrub_targets.pop(0), "scrub")

    # ── the walk: every knob driven while the hands watch ────────────────
    def _announce(self, text: str) -> None:
        self.hud.setText(text)
        self.hud.repaint()
        QApplication.processEvents()

    def _walk_scrub(self, n: int = 60, seed: int = 7,
                    pace_s: float = 0.03) -> None:
        rng = random.Random(seed)
        anchor = rng.randrange(SPAN)
        for _ in range(n):
            if rng.random() < 0.12:
                anchor = rng.randrange(SPAN)
            target = max(0, min(SPAN - 1, round(rng.gauss(anchor, 8))))
            self.request(target, "scrub")
            QApplication.processEvents()
            time.sleep(pace_s)

    def _walk_wait_fill(self, timeout_s: float = 90.0) -> bool:
        deadline = time.perf_counter() + timeout_s
        while len(self.cache) < SPAN and time.perf_counter() < deadline:
            if not self.fill.running():
                return len(self.cache) >= SPAN
            QApplication.processEvents()
            time.sleep(0.05)
        return len(self.cache) >= SPAN

    def _walk(self) -> None:
        if self._busy:
            return
        self.walk_btn.setEnabled(False)
        try:
            # leg 1: each miss policy against a cold cache, no fill
            for idx, label in ((0, "block: the honest ~300 ms"),
                               (1, "kf-snap: wrong by Δ, ~50 ms"),
                               (2, "nearest-cached: instant, wrong by Δ")):
                self._reset()
                self.miss_box.setCurrentIndex(idx)
                self._announce(f"[walk] miss policy — {label}")
                self._walk_scrub(40)

            # leg 2: fill orders x chunk sizes against the scripted scrub
            self.miss_box.setCurrentIndex(0)
            for fill_idx, chunk_idx in ((1, 0), (1, 2), (2, 2)):
                self._reset()
                self.chunk_box.setCurrentIndex(chunk_idx)
                self.fill_box.setCurrentIndex(fill_idx)
                self._announce(
                    f"[walk] {self.fill_box.currentText()} · "
                    f"{self.chunk_box.currentText()} — feel the misses "
                    "thin out (02: sequential + big chunks wins)")
                self._walk_scrub(80)

            # leg 3: the pollution story (03)
            for bypass, tag in ((False, "play FILLS the cache — watch the "
                                        "return scrub stall"),
                                (True, "play BYPASSES — the return scrub "
                                       "stays hot")):
                self._reset()
                self.miss_box.setCurrentIndex(0)
                self.budget_spin.setValue(60)
                self.bypass.setChecked(bypass)
                self._announce(f"[walk] pollution: {tag}")
                self._walk_scrub(40, seed=11)
                self._announce("[walk] play thru…")
                self._play_through()
                self._announce("[walk] …and back to where you were")
                self._walk_scrub(40, seed=11)
            self.budget_spin.setValue(SPAN)
            self.bypass.setChecked(True)

            # leg 4: the happy path — fill, persist, evict onto the cut, flow
            self._reset()
            self.chunk_box.setCurrentIndex(2)
            self.fill_box.setCurrentIndex(1)
            self._announce("[walk] filling to full coverage…")
            if not self._walk_wait_fill():
                self._announce("[walk] fill did not complete; stopping here")
                return
            self._announce("[walk] persisting the cut from RAM…")
            wall = self._encode_cut(self.cache.snapshot())
            self._persist_landed(wall)
            self._announce(
                f"[walk] cut landed in {wall:.1f}s — shrinking RAM to 30 "
                "frames, hopping: routes go cut, not miss")
            self.budget_spin.setValue(30)
            for _ in range(30):
                self.request(self._rng.randrange(SPAN), "hop")
                QApplication.processEvents()
                time.sleep(0.02)
            self._announce("[walk] re-paying flow over what RAM still holds…")
            snapshot = self.cache.snapshot()
            arrays = [snapshot[k] for k in sorted(snapshot)]
            if len(arrays) >= 2:
                wall = self._flow_sweep(arrays)
                self._flow_landed(wall, len(arrays))
            self._save_log()
            self._redraw_graphs()
            self._announce(
                "[walk] done — stats compare every leg; budget is 30 and "
                "the cut is live, so keep hopping to feel the tier order")
        finally:
            self.walk_btn.setEnabled(True)

    # ── persist / flow / reset ───────────────────────────────────────────
    @staticmethod
    def _encode_cut(snapshot: dict[int, np.ndarray]) -> float:
        before = time.perf_counter()
        GROWN_CUT.parent.mkdir(exist_ok=True)
        with av.open(str(GROWN_CUT), "w") as out:
            stream = out.add_stream("libx264", rate=24)
            stream.width, stream.height = CROP_W, CROP_H
            stream.pix_fmt = "yuv420p"
            stream.options = {"crf": "18", "preset": "veryfast", "g": "1"}
            for i in range(SPAN):
                vf = av.VideoFrame.from_ndarray(snapshot[i], format="gray")
                vf = vf.reformat(format="yuv420p")
                for pkt in stream.encode(vf):
                    out.mux(pkt)
            for pkt in stream.encode():
                out.mux(pkt)
        return time.perf_counter() - before

    def _persist_landed(self, wall: float) -> None:
        self.cut = CutFetcher(GROWN_CUT)
        if self.run:
            self.run.walls.append(
                {"what": "persist", "wall_s": round(wall, 2),
                 "detail": f"{GROWN_CUT.stat().st_size} bytes"})
        self.hud.setText(
            f"cut persisted in {wall:.2f}s ({GROWN_CUT.stat().st_size:,} "
            "bytes) — shrink the RAM budget and misses now land on it")
        self.persist_btn.setEnabled(True)
        self._touch()

    def _persist_broke(self, err: str) -> None:
        self.hud.setText(f"background work failed: {err}")
        self.persist_btn.setEnabled(True)
        self.flow_btn.setEnabled(True)

    def _persist(self) -> None:
        if len(self.cache) < SPAN:
            self.hud.setText(
                f"persist needs full coverage ({len(self.cache)}/{SPAN} "
                "cached) — turn fill on and let it finish, or raise the "
                "budget")
            return
        self.persist_btn.setEnabled(False)
        self.hud.setText("persisting from RAM…")
        snapshot = self.cache.snapshot()

        def worker():
            try:
                wall = self._encode_cut(snapshot)
            except Exception as exc:  # noqa: BLE001
                self.persist_failed.emit(repr(exc)[:200])
                return
            self.persist_done.emit(wall)  # queued to the GUI thread

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _flow_sweep(arrays: list[np.ndarray]) -> float:
        dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
        before = time.perf_counter()
        prev = arrays[0]
        for cur in arrays[1:]:
            flow = dis.calc(prev, cur, None)
            float(np.mean(np.abs(flow)))
            prev = cur
        return time.perf_counter() - before

    def _flow_landed(self, wall: float, n: int) -> None:
        if self.run:
            self.run.walls.append(
                {"what": "flow", "wall_s": round(wall, 2),
                 "detail": f"{n} frames"})
        self.hud.setText(
            f"flow re-paid over {n} frames in {wall:.2f}s — what a "
            "flow-parameter slider costs on this region")
        self.flow_btn.setEnabled(True)
        self._touch()

    def _flow(self) -> None:
        snapshot = self.cache.snapshot()
        if len(snapshot) < 2:
            self.hud.setText("re-pay flow: nothing cached yet")
            return
        self.flow_btn.setEnabled(False)
        self.hud.setText(f"flow over {len(snapshot)} cached frames…")
        arrays = [snapshot[k] for k in sorted(snapshot)]

        def worker():
            try:
                wall = self._flow_sweep(arrays)
            except Exception as exc:  # noqa: BLE001
                self.persist_failed.emit(f"flow: {exc!r}"[:200])
                return
            self.flow_done.emit(wall, len(arrays))

        threading.Thread(target=worker, daemon=True).start()

    def _reset(self) -> None:
        self.fill.stop()
        if self.frontier:
            self.frontier.stop()
            self.frontier = None
        self.fill = FillWorker(self.base_idx)
        self.cache = RamTier(self.budget_spin.value())
        with self.skel_lock:
            self.skeleton.clear()
        self.store.wipe()
        if self.cut:
            self.cut.close()
            self.cut = None
        GROWN_CUT.unlink(missing_ok=True)
        self.fill_box.setCurrentIndex(0)
        self.pos = 0
        self._recent_targets.clear()
        self.hud.setText("cold again: nothing cached, no cut, no chunks, "
                         "fill off")
        self._touch()

    # ── status, graphs, log ──────────────────────────────────────────────
    def _refresh_status(self) -> None:
        blocks = 60
        per = SPAN / blocks
        with self.cache.lock:
            dense = set(self.cache.d.keys())
        if self.frontier:
            persisted = self.frontier.persisted
            with self.skel_lock:
                skel = set(self.skeleton.keys())
            def cell(b: int) -> str:
                lo, hi = int(b * per), int((b + 1) * per)
                if any(lo <= k < hi for k in dense):
                    return "█"    # in RAM, exact
                if any(lo <= s < hi or lo < s + CHUNK_FRAMES <= hi
                       for s in persisted):
                    return "▄"    # on disk, ~10 ms away
                if any(lo <= k < hi for k in skel):
                    return "·"    # skeleton only: nearest within Δ12
                return " "
            bar = "".join(cell(b) for b in range(blocks))
            self.coverage.setText(
                f"[{bar}] ram {len(dense)} · skel {len(skel)} · "
                f"chunks {len(persisted)}/{-(-SPAN // CHUNK_FRAMES)} · "
                f"frontier@{self.frontier.frontier_pos}")
        else:
            bar = "".join(
                "█" if any(int(b * per) <= k < int((b + 1) * per)
                           for k in dense)
                else "·" for b in range(blocks))
            self.coverage.setText(
                f"cache [{bar}] {len(dense)}/{SPAN}"
                + (f" · fill {'running' if self.fill.running() else 'idle'}"
                   f" {len(self.fill.filled)}/{SPAN}" if self.fill else "")
                + (" · cut on disk" if self.cut else ""))
        self.status.setText(self._config())

    def _touch(self) -> None:
        if not self._graph_timer.isActive():
            self._graph_timer.start()
        if not self._save_timer.isActive():
            self._save_timer.start()

    def _ordered_runs(self) -> list[RunLog]:
        return [r for r in self.runs.values() if r.events or r.walls]

    def _redraw_graphs(self) -> None:
        if self._busy or self._play_timer.isActive():
            self._graph_timer.start(1200)
            return
        runs = self._ordered_runs()
        cmap = matplotlib.colormaps["tab10"]
        fig = self.trace_fig
        fig.clear()
        ax = fig.add_subplot(111)
        for index, run in enumerate(runs):
            color = cmap(index % 10)
            first = True
            for task, marker in TASK_MARKERS.items():
                xs = [i for i, e in enumerate(run.events)
                      if e["task"] == task]
                ys = [run.events[i]["ms"] for i in xs]
                if xs:
                    ax.scatter(xs, ys, s=14, marker=marker, color=color,
                               alpha=0.7, label=run.label if first else None)
                    first = False
        if runs:
            ax.set_yscale("log")
            ax.grid(True, which="both", alpha=0.25)
            ax.legend(fontsize=7, loc="best")
        else:
            ax.set_axis_off()
        ax.set_xlabel("request # per run")
        ax.set_ylabel("ms (log)")
        ax.set_title("every request this launch, by stack config")
        self.trace_canvas.draw_idle()
        self.stats.setPlainText("\n\n".join(r.stats_text() for r in runs))

    def _save_log(self) -> None:
        if self._busy:
            self._save_timer.start(1500)
            return
        payload = {
            "tool": "storage-explorer.py",
            "when": datetime.now(timezone.utc).isoformat(),
            "sieve_rev": harness._sieve_rev(),
            "machine": harness._machine(),
            "versions": harness._versions(),
            "span": SPAN, "gop": GOP, "near_radius": NEAR_RADIUS,
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
        self.fill.stop()
        if self.frontier:
            self.frontier.stop()
        self._save_log()
        self.miss_fetcher.close()
        if self.cut:
            self.cut.close()
        self.store.wipe()
        GROWN_CUT.unlink(missing_ok=True)
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Right:
            self.request(self.pos + 1, "step")
        elif key == Qt.Key.Key_Left:
            self.request(self.pos - 1, "step")
        elif key == Qt.Key.Key_Space:
            self.play_btn.toggle()
        else:
            super().keyPressEvent(event)


def main() -> None:
    if not BIG.exists():
        print(f"missing {BIG}")
        return
    app = QApplication.instance() or QApplication(sys.argv)
    window = StorageExplorer()
    if "--walk" in sys.argv:  # headless validation of the full walk
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        window._walk()
        print(window.hud.text())
        data = json.loads(window.log_path.read_text(encoding="utf-8"))
        print(f"walk ok: {len(data['runs'])} configs logged to "
              f"{window.log_path.name}")
        window.fill.stop()
        if window.cut:  # Windows will not unlink a file still held open
            window.cut.close()
            window.cut = None
        GROWN_CUT.unlink(missing_ok=True)
        return
    if "--smoke" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        for rel in (5, 6, 30):
            window.request(rel, "drag")
        window.miss_box.setCurrentIndex(1)
        window.request(80, "drag")
        window.miss_box.setCurrentIndex(2)
        window.request(82, "drag")
        print(window.hud.text())
        window.fill_box.setCurrentIndex(1)
        time.sleep(3.0)
        window.request(40, "drag")
        print(window.hud.text())
        # composite: frontier + skeleton + chunk store
        window._reset()
        window.fill_box.setCurrentIndex(3)
        time.sleep(4.0)
        window.request(250, "drag")   # ahead of the frontier: near/skel
        print(window.hud.text())
        window.budget_spin.setValue(10)  # force eviction onto the chunks
        time.sleep(1.0)
        window.request(20, "drag")
        print(window.hud.text())
        window._refresh_status()
        print(window.coverage.text())
        window._redraw_graphs()
        window._save_log()
        data = json.loads(window.log_path.read_text(encoding="utf-8"))
        print(f"smoke ok: {len(data['runs'])} runs logged to "
              f"{window.log_path.name}")
        window.fill.stop()
        return
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
