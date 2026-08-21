"""Feel the decode approaches by hand: scrub, play, step and sweep each backend.

The result files say what a seek costs; this is where that number becomes a
sensation. Pick a source (uncut 5.3K, the cut clips, the small H.264) and an
approach (PyAV luma threaded or single-thread, BGR, CUDA, cv2), then do the
things SIEVE does: drag the scrub bar, play, arrow-step, and "sweep" — decode
a block flat out, which is what refilling a graph is. The HUD prints what
every request cost and which route it took (seek, step, cached).

Every (source, approach) pair is a *run*: its requests accumulate whether or
not you switch away and come back, the right-hand graphs overlay every run
touched this launch (trace of each request; p50/p95 per task in comparison),
and the whole thing autosaves to explorer-logs/ as one JSON per launch — so a
later session can read what the hands felt rather than asking.

Two policy knobs are the point, because they are the subsystems v2/v3 built:
"step if within" is the scrub policy's crossover (0 = always seek), and
"drop stale drags" is the coalescer (off = every mouse move queues, which is
the naive viewer). Toggle them on the uncut source and the architecture
argues for itself.

Run:
    uv run --group experiments python experiments/decode-experiments/explorer.py
"""

from __future__ import annotations

import json
import platform
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import av
import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
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

import harness  # noqa: E402
from harness import FOOTAGE, quantiles  # noqa: E402

LOGS = Path(__file__).resolve().parent / "explorer-logs"
#: Seek-probe verdicts, keyed by machine|codec|resolution. The probe costs
#: several real seeks, so each machine pays it once per source shape and
#: remembers; delete the file to force re-probing (new GPU, new driver).
PROBE_CACHE = LOGS / "probe-cache.json"


def probe_cache_load() -> dict:
    try:
        return json.loads(PROBE_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def probe_cache_store(key: str, entry: dict) -> None:
    data = probe_cache_load()
    data[key] = entry
    PROBE_CACHE.parent.mkdir(exist_ok=True)
    PROBE_CACHE.write_text(json.dumps(data, indent=1), encoding="utf-8")

APPROACHES = {
    "pyav · luma · threads=auto": "luma-auto",
    "pyav · luma · threads=1": "luma-t1",
    "pyav · bgr24 (cached reformatter)": "bgr24",
    "pyav · cuda hw · luma": "cuda",
    "cv2 · read BGR": "cv2",
    "hybrid · sw steps + cuda seeks": "hybrid",
    "pyav · luma ↓display (strided)": "luma-ds",
    "hybrid ↓display + LRU cache": "hybrid-ds-cache",
    "cuda ↓display + LRU cache": "cuda-ds-cache",
    "bgr24 ↓display + LRU cache": "bgr-ds-cache",
    "chroma-mask · UV planes ¼ res": "chroma-mask",
}
#: Approaches the hands have already ruled out, kept visible but unselectable
#: so the list still says what was tried. Reasons cite the session logs.
RETIRED = {
    "pyav · luma · threads=1":
        "retired: 900 ms drags, 9.7 fps play (explorer-logs 17:26)",
    "cv2 · read BGR":
        "retired: the losing colour route — bgr24-cached drags 2.6x faster "
        "and has kf-snap (17:26)",
    "pyav · luma · threads=auto":
        "retired: dominated by the ↓display variant on every felt metric (17:34)",
    "pyav · luma ↓display (strided)":
        "retired: hybrid ↓display + cache strictly adds hw seeks and revisit "
        "cache over it (18:14)",
    "pyav · bgr24 (cached reformatter)":
        "retired: for seeing colour, ↓display+cache scales before converting "
        "(1.6 ms); for computing on colour, the chroma planes are already "
        "decoded",
    "hybrid · sw steps + cuda seeks":
        "retired: the ↓display + cache variant strictly adds the display "
        "reduction and the revisit cache",
    "pyav · cuda hw · luma":
        "retired: dominated by cuda ↓display + cache on every interactive "
        "mode, and hw seeks lose outright below ~4 MP (18:29, 18:36)",
}
TASK_MARKERS = {"drag": "o", "play": ".", "rev": "v", "step": "^",
                "open": "s", "hop": "x", "batch": "d"}
#: Per-session event cap; a forgotten play session should not eat the log.
EVENT_CAP = 20_000


def list_sources() -> list[Path]:
    found: list[Path] = []
    for folder in (FOOTAGE, FOOTAGE / "derived"):
        if folder.is_dir():
            found += sorted(
                p for p in folder.iterdir()
                if p.suffix.lower() in (".mp4", ".mkv", ".mov", ".avi")
            )
    return found


# ── sources ──────────────────────────────────────────────────────────────────
class PyAVSource:
    """One open container with a position, stepping or seeking on request."""

    supports_keyframe = True

    def __init__(self, path: Path, *, luma: bool, thread_count: int = 0,
                 hwaccel: str | None = None, display_width: int | None = None,
                 chroma_mask: bool = False):
        self.display_width = display_width
        self.chroma_mask = chroma_mask
        opts = {}
        if hwaccel:
            from av.codec.hwaccel import HWAccel

            opts["hwaccel"] = HWAccel(device_type=hwaccel,
                                      allow_software_fallback=False)
        self.container = av.open(str(path), **opts)
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.stream.codec_context.thread_count = thread_count
        self.luma = luma
        if not luma:
            from av.video.reformatter import VideoReformatter

            self.reformatter = VideoReformatter()
        tb, rate = self.stream.time_base, self.stream.average_rate
        self.fps = float(rate)
        self.nframes = self.stream.frames
        if not self.nframes:  # Matroska (the FFV1 cut) stores no count
            if self.stream.duration:
                self.nframes = int(self.stream.duration * tb * rate)
            elif self.container.duration:
                self.nframes = int(self.container.duration / 1_000_000 * rate)
        self._base = self.stream.start_time or 0
        self._step_pts = Fraction(1, 1) / (rate * tb)
        self._decoded = self.container.decode(self.stream)
        self.pos = -1

    def _pts_of(self, idx: int) -> int:
        return self._base + int(self._step_pts * idx)

    @staticmethod
    def _plane_view(plane, width: int, height: int) -> np.ndarray:
        arr = np.frombuffer(plane, dtype=np.uint8)
        arr = arr[: height * plane.line_size]
        return arr.reshape(height, plane.line_size)[:, :width]

    def _image(self, frame) -> np.ndarray:
        if self.chroma_mask:
            # colourfulness straight off the decoder's chroma planes: 4:2:0
            # stores U and V at quarter resolution, already decoded, so a
            # |U-128|+|V-128| threshold costs quarter-size numpy and no
            # swscale. It is chroma magnitude, not HSV saturation — it
            # scales with brightness — but for "is this pixel strongly
            # coloured" it is the free version of the same question.
            half_w, half_h = frame.width // 2, frame.height // 2
            u = np.ascontiguousarray(
                self._plane_view(frame.planes[1], half_w, half_h))
            v = np.ascontiguousarray(
                self._plane_view(frame.planes[2], half_w, half_h))
            mag = cv2.add(cv2.absdiff(u, 128), cv2.absdiff(v, 128))
            return cv2.threshold(mag, 20, 255, cv2.THRESH_BINARY)[1]
        if self.luma:
            arr = self._plane_view(frame.planes[0], frame.width, frame.height)
            if self.display_width and frame.width > self.display_width:
                stride = -(-frame.width // self.display_width)  # ceil
                arr = arr[::stride, ::stride]  # reduce before the copy
            return np.ascontiguousarray(arr)
        if self.display_width and frame.width > self.display_width:
            # scale and convert in one swscale pass: full colour at display
            # size costs a fraction of full-resolution BGR
            height = int(frame.height * self.display_width
                         / frame.width) // 2 * 2
            return self.reformatter.reformat(
                frame, width=self.display_width, height=height,
                format="bgr24").to_ndarray()
        return self.reformatter.reformat(frame, format="bgr24").to_ndarray()

    def get(self, idx: int, step_within: int, mode: str = "exact",
            prefer: str = "latency") -> tuple[np.ndarray, str]:
        ahead = idx - self.pos
        if 0 < ahead <= step_within:  # exact and cheaper than any snap
            for _ in range(ahead):
                frame = next(self._decoded)
            self.pos = idx
            return self._image(frame), f"step ×{ahead}"
        target = self._pts_of(idx)
        half = self._step_pts / 2
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        if mode == "keyframe":  # storyboard scrub: one decode, no roll-forward
            frame = next(self._decoded)
            landed = round((frame.pts - self._base) / self._step_pts)
            self.pos = landed
            return self._image(frame), f"kf-snap Δ{idx - landed}"
        for frame in self._decoded:
            if frame.pts is not None and frame.pts + half >= target:
                break
        self.pos = idx
        return self._image(frame), "seek"

    def close(self) -> None:
        self.container.close()


class Cv2Source:
    """cv2.VideoCapture behind the same get(); retrieve only on the landing frame."""

    luma = False
    supports_keyframe = False

    def __init__(self, path: Path):
        self.cap = cv2.VideoCapture(str(path))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.nframes = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.pos = -1

    def get(self, idx: int, step_within: int, mode: str = "exact",
            prefer: str = "latency") -> tuple[np.ndarray, str]:
        ahead = idx - self.pos
        if 0 < ahead <= step_within:
            for _ in range(ahead):
                self.cap.grab()
            route = f"step ×{ahead}"
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            self.cap.grab()
            route = "seek"
        ok, img = self.cap.retrieve()
        self.pos = idx
        if not ok:
            raise RuntimeError(f"cv2 retrieve failed at frame {idx}")
        return img, route

    def close(self) -> None:
        self.cap.release()


class HybridSource:
    """Two decoders on one file, each serving the task it measured fastest at.

    Software threads win sequential throughput and NVDEC wins seek latency
    (results/02-*, 03-*), so steps go to whichever decoder is already in
    position (software preferred), long jumps go to the hardware decoder, and
    a sweep asks for throughput and gets the software one outright."""

    luma = True
    supports_keyframe = True

    def __init__(self, path: Path, display_width: int | None = None):
        self.sw = PyAVSource(path, luma=True, display_width=display_width)
        try:
            self.hw = PyAVSource(path, luma=True, hwaccel="cuda",
                                 display_width=display_width)
        except Exception:  # noqa: BLE001 - no cuda is a fine hybrid
            self.hw = None
        self.probe_ms: dict[str, float] = {}
        self.probe_cached = False
        stream = self.sw.stream
        cache_key = (f"{platform.node()}|{stream.codec_context.name}"
                     f"|{stream.width}x{stream.height}")
        cached = probe_cache_load().get(cache_key) if self.hw else None
        if cached:
            self.probe_ms = cached.get("probe_ms", {})
            self.probe_cached = True
            if cached.get("winner") == "sw" and self.hw is not None:
                self.hw.close()
                self.hw = None
        elif self.hw is not None and self.sw.nframes > 10:
            # Route seeks by measurement, not this machine's folklore: which
            # side lands a random frame faster depends on GPU, core count
            # and frame size (on one 22-core/RTX-4060 box hw won only above
            # ~4 MP), so the pair is probed once at open and the loser of
            # the seek race carries nothing.
            # One seek is not a measurement: the first hw seek pays CUDA
            # warmup and misroutes the pair (probe said hw 287 ms where
            # sustained use measures ~109). Same discipline as the harness:
            # a warmup seek is discarded, the best of two counted ones wins.
            third = self.sw.nframes // 3
            for side, source, base in (("sw", self.sw, third),
                                       ("hw", self.hw, 2 * third)):
                times = []
                for k in range(3):
                    begin = time.perf_counter()
                    source.get(base + 7 * k, 0)
                    times.append((time.perf_counter() - begin) * 1000)
                self.probe_ms[side] = min(times[1:])
            winner = "hw" if self.probe_ms["hw"] <= self.probe_ms["sw"] else "sw"
            probe_cache_store(cache_key, {
                "winner": winner, "probe_ms": self.probe_ms,
                "when": datetime.now(timezone.utc).isoformat(),
            })
            if winner == "sw":
                self.hw.close()
                self.hw = None
        self.fps = self.sw.fps
        self.nframes = self.sw.nframes
        self.pos = -1

    def get(self, idx: int, step_within: int, mode: str = "exact",
            prefer: str = "latency") -> tuple[np.ndarray, str]:
        if self.hw is None or prefer == "throughput":
            # catch-up stepping breaks even with a sw seek near 60 frames
            # (~300 ms seek / ~5 ms per stepped frame, results/02-*, 01-*),
            # so a parked sw decoder seeks rather than walking the gap
            within = 60 if prefer == "throughput" else step_within
            image, route = self.sw.get(idx, within, mode)
            side = "sw"
        elif mode == "keyframe":
            image, route = self.hw.get(idx, 0, mode="keyframe")
            side = "hw"
        elif 0 < idx - self.sw.pos <= step_within:
            image, route = self.sw.get(idx, step_within)
            side = "sw"
        elif 0 < idx - self.hw.pos <= step_within:
            image, route = self.hw.get(idx, step_within)
            side = "hw"
        else:
            image, route = self.hw.get(idx, 0)
            side = "hw"
        self.pos = self.hw.pos if side == "hw" else self.sw.pos
        return image, f"{side} {route}"

    def close(self) -> None:
        self.sw.close()
        if self.hw is not None:
            self.hw.close()


class CachedSource:
    """LRU frame cache over any source; a revisited frame costs a dict hit.

    This is the composition ideas.md wants — a caching source wrapping a
    decoding source — and it also makes one failure mode feelable: play fills
    the cache and evicts exactly the frames a drag returned to, so 'playback
    should not fill the scrub cache' stops being a slogan. Route says 'cache'
    on a hit; capacity is a byte budget, so strided display frames cache
    ~15x more of the timeline than full-resolution luma."""

    def __init__(self, inner, budget_bytes: int = 1_500_000_000):
        self.inner = inner
        self.fps = inner.fps
        self.nframes = inner.nframes
        self.luma = getattr(inner, "luma", True)
        self.supports_keyframe = getattr(inner, "supports_keyframe", False)
        self._cache: dict[int, np.ndarray] = {}
        self._order: deque[int] = deque()
        self._bytes = 0
        self._budget = budget_bytes
        self._pos = -1

    @property
    def pos(self) -> int:
        # the cache's own position, not the inner decoder's: a cache hit
        # advances it without the decoder moving, else free-run play parks
        # on the first cached frame forever
        return self._pos

    def get(self, idx: int, step_within: int, mode: str = "exact",
            prefer: str = "latency") -> tuple[np.ndarray, str]:
        if idx in self._cache:  # exact hit serves even a keyframe request
            self._pos = idx
            return self._cache[idx], "cache"
        image, route = self.inner.get(idx, step_within, mode, prefer)
        landed = self.inner.pos
        self._pos = landed
        if landed not in self._cache:
            self._cache[landed] = image
            self._order.append(landed)
            self._bytes += image.nbytes
            while self._bytes > self._budget and self._order:
                old = self._order.popleft()
                self._bytes -= self._cache.pop(old).nbytes
        return image, route

    def close(self) -> None:
        self.inner.close()


def make_source(path: Path, approach: str):
    if approach.startswith("cv2"):
        return Cv2Source(path)
    if "cache" in approach and "hybrid" in approach:
        return CachedSource(HybridSource(path, display_width=1400))
    if "cache" in approach and "cuda" in approach:
        return CachedSource(PyAVSource(path, luma=True, hwaccel="cuda",
                                       display_width=1400))
    if "cache" in approach and "bgr24" in approach:
        return CachedSource(PyAVSource(path, luma=False,
                                       display_width=1400))
    if "chroma-mask" in approach:
        return PyAVSource(path, luma=True, chroma_mask=True)
    if approach.startswith("hybrid"):
        return HybridSource(path)
    if "↓display" in approach:
        return PyAVSource(path, luma=True, display_width=1400)
    if "cuda" in approach:
        return PyAVSource(path, luma=True, hwaccel="cuda")
    if "bgr24" in approach:
        return PyAVSource(path, luma=False)
    threads = 1 if "threads=1" in approach else 0
    return PyAVSource(path, luma=True, thread_count=threads)


# ── runs: what accumulates and what gets saved ───────────────────────────────
class RunLog:
    """Everything one (source, approach) pair was asked to do this launch."""

    def __init__(self, source_name: str, approach: str, fps: float, nframes: int):
        self.source = source_name
        self.approach = approach
        self.label = f"{Path(source_name).stem[:16]} · {APPROACHES.get(approach, approach)}"
        self.fps = fps
        self.nframes = nframes
        self.started = datetime.now(timezone.utc).isoformat()
        self._t0 = time.perf_counter()
        self.events: list[dict] = []
        self.sweeps: list[dict] = []
        self.capped = False

    def log(self, task: str, frame: int, route: str,
            decode_ms: float, display_ms: float) -> None:
        if len(self.events) >= EVENT_CAP:
            self.capped = True
            return
        self.events.append({
            "t": round(time.perf_counter() - self._t0, 4),
            "task": task, "frame": frame, "route": route,
            "ms": round(decode_ms, 3), "disp": round(display_ms, 3),
        })

    def summary(self) -> dict:
        by_task: dict[str, dict] = {}
        for task in ("drag", "play", "rev", "step", "open", "hop", "batch"):
            samples = [e["ms"] for e in self.events if e["task"] == task]
            if samples:
                by_task[task] = {"n": len(samples), **{
                    k: round(v, 2) for k, v in quantiles(samples).items()}}
        play_times = [e["t"] for e in self.events if e["task"] == "play"]
        gaps = [b - a for a, b in zip(play_times, play_times[1:]) if b - a < 0.5]
        achieved = round(len(gaps) / sum(gaps), 2) if gaps else None
        seeks = [e["ms"] for e in self.events if e["route"] == "seek"]
        return {
            "label": self.label, "source": self.source, "approach": self.approach,
            "target_fps": round(self.fps, 3), "by_task": by_task,
            "play_achieved_fps": achieved,
            "seek_p50_ms": round(quantiles(seeks)["p50"], 2) if seeks else None,
            "sweeps": self.sweeps, "events_capped": self.capped,
        }

    def stats_text(self) -> str:
        s = self.summary()
        lines = [self.label]
        for task, q in s["by_task"].items():
            lines.append(
                f"  {task:<5} n={q['n']:<5} p50={q['p50']:>8.1f}"
                f"  p95={q['p95']:>8.1f}  max={q['max']:>8.1f} ms")
        if s["play_achieved_fps"]:
            lines.append(
                f"  play  achieved {s['play_achieved_fps']:.1f} fps"
                f"  (target {self.fps:.2f})")
        for sw in self.sweeps[-3:]:
            kind = "sweep∥" if "parallel" in sw else "sweep"
            lines.append(
                f"  {kind} {sw['frames']}f in {sw['wall_s']:.2f}s"
                f" = {sw['fps']:.0f} fps ({sw['fps'] / self.fps:.1f}×)")
        if self.capped:
            lines.append(f"  (events capped at {EVENT_CAP})")
        return "\n".join(lines)


# ── the window ───────────────────────────────────────────────────────────────
class Explorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("decode explorer — feel the approaches")
        self.resize(1680, 900)
        self.source = None
        self.run: RunLog | None = None
        self.runs: dict[tuple[str, str], RunLog] = {}
        self._queue: deque[int] = deque()
        self._busy = False
        self._recent: deque[float] = deque(maxlen=30)
        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._play_tick)
        LOGS.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS / f"explorer-{stamp}.json"
        self._graph_timer = QTimer(self, singleShot=True, interval=600)
        self._graph_timer.timeout.connect(self._redraw_graphs)
        self._save_timer = QTimer(self, singleShot=True, interval=2500)
        self._save_timer.timeout.connect(self._save_log)

        self.file_box = QComboBox()
        self.paths = list_sources()
        for p in self.paths:
            self.file_box.addItem(
                f"{p.name}" + ("  (derived)" if p.parent.name == "derived" else ""))
        self.approach_box = QComboBox()
        self.approach_box.addItems(
            [a for a in APPROACHES if a not in RETIRED])
        self.approach_box.setCurrentText("hybrid · sw steps + cuda seeks")
        self.file_box.currentIndexChanged.connect(self._reopen)
        self.approach_box.currentIndexChanged.connect(self._reopen)

        self.step_within = QSpinBox(minimum=0, maximum=10_000, value=40)
        self.step_within.setToolTip(
            "scrub policy: step forward instead of seeking when the target is "
            "within this many frames (0 = always seek). 40 is the measured "
            "crossover on the uncut 5.3K source; see results/02-*.json")
        self.coalesce = QCheckBox("drop stale drags")
        self.coalesce.setChecked(True)
        self.coalesce.setToolTip(
            "the coalescer: only the latest scrub target is served. Off = "
            "every mouse move queues, which is the naive viewer.")
        self.snap = QCheckBox("kf-snap drags")
        self.snap.setToolTip(
            "storyboard scrub: while dragging, serve the nearest keyframe "
            "(one decode, no roll-forward) and the exact frame on release. "
            "GOP is 24 on the 5.3K source, so the snap is at most ~half a "
            "second of timeline; the HUD prints each snap's Δ.")

        self.play_btn = QPushButton("play")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self._toggle_play)
        self.rev_btn = QPushButton("play ◀")
        self.rev_btn.setCheckable(True)
        self.rev_btn.setToolTip(
            "reverse play, free-run: the pathological case for inter-coded "
            "video — every backward frame is a fresh seek on the uncut "
            "source, and nothing at all on intra clips and the proxy")
        self.rev_btn.toggled.connect(self._toggle_rev)
        self.hop_btn = QPushButton("hop")
        self.hop_btn.setCheckable(True)
        self.hop_btn.setToolTip(
            "uniform-random frames, free-run: sustained random access, "
            "which is the tuning loop's actual access pattern")
        self.hop_btn.toggled.connect(self._toggle_hop)
        self.batch_btn = QPushButton("batch 32")
        self.batch_btn.setToolTip(
            "fetch 32 random frames as one sorted, crossover-aware forward "
            "pass — the decord technique. Compare its ms/frame against the "
            "hop rate: sorting only wins when targets are dense")
        self.batch_btn.clicked.connect(self._batch)
        self._dir = 1
        self._hop = False
        import random as _random

        self._rng = _random.Random()
        self.sweep_btn = QPushButton("sweep 300")
        self.sweep_btn.setToolTip(
            "decode 300 frames forward flat out — what refilling a graph is")
        self.sweep_btn.clicked.connect(self._sweep)
        self.psweep_shape = QComboBox()
        self.psweep_shape.addItems(["1sw+1hw", "2sw+1hw", "4sw+1hw"])
        self.psweep_shape.setToolTip(
            "how many decoders share the machine. First press of 4sw+1hw "
            "measured software workers collapsing 190→30 fps each while "
            "NVDEC held ~100 — contention is real and the lean shape wins.")
        self.psweep_btn = QPushButton("sweep ∥")
        self.psweep_btn.setToolTip(
            "the pipeline shape: fresh decoders each take a 300-frame "
            "GOP-aligned chunk in parallel. Aggregate fps is what a "
            "whole-video pass costs; per-worker fps shows what sharing the "
            "machine does to the single-stream numbers.")
        self.psweep_btn.clicked.connect(self._sweep_parallel)
        self.testall_btn = QPushButton("test all")
        self.testall_btn.setToolTip(
            "run every surviving approach through every mode on the current "
            "source — drags, play, reverse, hop, batch, sweep, and one lean "
            "parallel pipeline sweep — so no combination goes unmeasured. "
            "Everything lands in the graphs and the log as usual.")
        self.testall_btn.clicked.connect(self._test_all)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("source:"))
        row1.addWidget(self.file_box, 2)
        row1.addWidget(QLabel("approach:"))
        row1.addWidget(self.approach_box, 2)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("step if within:"))
        row2.addWidget(self.step_within)
        row2.addWidget(self.coalesce)
        row2.addWidget(self.snap)
        row2.addStretch(1)
        row2.addWidget(self.play_btn)
        row2.addWidget(self.rev_btn)
        row2.addWidget(self.hop_btn)
        row2.addWidget(self.batch_btn)
        row2.addWidget(self.sweep_btn)
        row2.addWidget(self.psweep_btn)
        row2.addWidget(self.psweep_shape)
        row2.addWidget(self.testall_btn)
        top = QVBoxLayout()
        top.addLayout(row1)
        top.addLayout(row2)

        self.canvas = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.canvas.setMinimumSize(280, 180)  # an instrument, not a cinema
        self.canvas.setStyleSheet("background: #101010;")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.sliderMoved.connect(lambda i: self.request(i, "drag"))
        self.slider.valueChanged.connect(lambda i: self.request(i, "drag"))
        self.slider.sliderReleased.connect(
            lambda: self.request(self.slider.value(), "drag", exact=True))

        self.hud = QLabel("open a source")
        self.hud.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10pt; padding: 3px;")
        self.history = QLabel("")
        self.history.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 9pt; color: #888;")

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addLayout(top)
        left_layout.addWidget(self.canvas, 1)
        left_layout.addWidget(self.slider)
        left_layout.addWidget(self.hud)
        left_layout.addWidget(self.history)

        self.trace_fig = Figure(tight_layout=True)
        self.trace_canvas = FigureCanvasQTAgg(self.trace_fig)
        self.compare_fig = Figure(tight_layout=True)
        self.compare_canvas = FigureCanvasQTAgg(self.compare_fig)
        self.stats = QPlainTextEdit(readOnly=True)
        self.stats.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 9pt;")
        clear_btn = QPushButton("clear runs")
        clear_btn.clicked.connect(self._clear_runs)
        save_lbl = QLabel(f"log: {self.log_path.name}")
        save_lbl.setStyleSheet("color: #888; font-size: 8pt;")
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.trace_canvas, 3)
        right_layout.addWidget(self.compare_canvas, 2)
        right_layout.addWidget(self.stats, 2)
        bottom = QHBoxLayout()
        bottom.addWidget(save_lbl, 1)
        bottom.addWidget(clear_btn)
        right_layout.addLayout(bottom)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([620, 1060])  # graphs are the product here
        self.setCentralWidget(splitter)
        self._reopen()

    # ── source lifecycle ─────────────────────────────────────────────────
    def _reopen(self, *_args) -> None:
        self.play_btn.setChecked(False)
        if self.source:
            self.source.close()
            self.source = None
        self.run = None
        if not self.paths:
            self.hud.setText(f"no footage found under {FOOTAGE}")
            return
        path = self.paths[self.file_box.currentIndex()]
        approach = self.approach_box.currentText()
        try:
            before = time.perf_counter()
            self.source = make_source(path, approach)
            open_ms = (time.perf_counter() - before) * 1000
        except Exception as exc:  # noqa: BLE001 - the failure is the datum
            self.hud.setText(f"{approach} cannot open {path.name}: {exc}")
            return
        key = (path.name, approach)
        if key not in self.runs:
            self.runs[key] = RunLog(path.name, approach,
                                    self.source.fps, self.source.nframes)
        self.run = self.runs[key]
        self._recent.clear()
        self._queue.clear()
        self.slider.blockSignals(True)
        self.slider.setMaximum(max(0, self.source.nframes - 1))
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.request(0, "open")
        probe = getattr(self.source, "probe_ms", None) or getattr(
            getattr(self.source, "inner", None), "probe_ms", None)
        verdict = ""
        if probe:
            winner = "hw" if probe["hw"] <= probe["sw"] else "sw"
            cached = getattr(self.source, "probe_cached", False) or getattr(
                getattr(self.source, "inner", None), "probe_cached", False)
            verdict = (f" · seek probe sw {probe['sw']:.0f} / hw "
                       f"{probe['hw']:.0f} ms → {winner} seeks"
                       + (" (cached)" if cached else ""))
        self.hud.setText(  # after request(0), so the verdict survives it
            f"{path.name} · {self.source.nframes} frames @ "
            f"{self.source.fps:.2f} fps · opened in {open_ms:.0f} ms{verdict}")

    # ── the request loop: SIEVE's viewer in one method ───────────────────
    def request(self, idx: int, task: str = "step", exact: bool = False) -> None:
        if not self.source:
            return
        mode = ("keyframe"
                if task == "drag" and not exact and self.snap.isChecked()
                and getattr(self.source, "supports_keyframe", False)
                else "exact")
        if self.coalesce.isChecked():
            self._queue.clear()
        self._queue.append(idx)
        if self._busy:
            return
        self._busy = True
        try:
            while self._queue:
                target = self._queue.popleft()
                depth = len(self._queue)
                try:
                    before = time.perf_counter()
                    image, route = self.source.get(
                        target, self.step_within.value(), mode=mode)
                    decode_ms = (time.perf_counter() - before) * 1000
                except Exception as exc:  # noqa: BLE001
                    self.hud.setText(f"frame {target}: {exc}")
                    continue
                before = time.perf_counter()
                self._show(image)
                display_ms = (time.perf_counter() - before) * 1000
                if self.run:
                    self.run.log(task, target, route, decode_ms, display_ms)
                self._recent.append(decode_ms)
                mean = sum(self._recent) / len(self._recent)
                self.hud.setText(
                    f"frame {target:>6} · {task:<4} · {route:<9}"
                    f" · decode {decode_ms:7.1f} ms · display {display_ms:5.1f} ms"
                    f" · last {len(self._recent)} mean {mean:6.1f} ms"
                    + (f" · queued {depth}" if depth else ""))
                self.history.setText("recent ms: " + "  ".join(
                    f"{ms:.0f}" for ms in list(self._recent)[-12:]))
                self.slider.blockSignals(True)
                self.slider.setValue(target)
                self.slider.blockSignals(False)
                QApplication.processEvents()  # let new drag targets land
        finally:
            self._busy = False
            self._touch()

    def _show(self, image: np.ndarray) -> None:
        if not image.flags.c_contiguous:  # QImage borrows the buffer raw
            image = np.ascontiguousarray(image)
        if image.ndim == 2:
            h, w = image.shape
            qimage = QImage(image.data, w, h, image.strides[0],
                            QImage.Format.Format_Grayscale8)
        else:
            h, w, _ = image.shape
            qimage = QImage(image.data, w, h, image.strides[0],
                            QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qimage)  # copies, so numpy buffer may die
        self.canvas.setPixmap(pixmap.scaled(
            self.canvas.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation))

    # ── play: realtime consumption ───────────────────────────────────────
    def _toggle_play(self, playing: bool) -> None:
        if playing:
            self._dir, self._hop = 1, False
            self.rev_btn.setChecked(False)
            self.hop_btn.setChecked(False)
        self._drive(playing, self.play_btn, "play")

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

    def _drive(self, on: bool, btn: QPushButton, idle_label: str) -> None:
        # free-run: no pacing, every event-loop turn decodes a frame.
        # Achieved fps against the file's native rate is the reading.
        if on and self.source:
            self._play_timer.start(0)
            btn.setText("pause")
            return
        btn.setText(idle_label)
        if not (self.play_btn.isChecked() or self.rev_btn.isChecked()
                or self.hop_btn.isChecked()):
            self._play_timer.stop()

    def _play_tick(self) -> None:
        if not self.source or self._busy:
            return  # a tick that arrives mid-decode is dropped, not queued
        if self._hop:
            self.request(self._rng.randrange(self.source.nframes), "hop")
            return
        nxt = self.source.pos + self._dir
        if nxt < 0 or nxt >= self.source.nframes:
            self.play_btn.setChecked(False)
            self.rev_btn.setChecked(False)
            return
        self.request(nxt, "play" if self._dir > 0 else "rev")

    def _batch(self) -> None:
        """32 random frames, sorted, one crossover-aware forward pass."""
        if not self.source or self._busy:
            return
        self._busy = True
        try:
            count = min(32, self.source.nframes)
            targets = sorted(self._rng.sample(range(self.source.nframes),
                                              count))
            # ~8 s of frozen UI on the uncut source otherwise reads as a hang
            self.hud.setText(f"batch {count} running…")
            self.hud.repaint()
            before = time.perf_counter()
            image = None
            for target in targets:
                t0 = time.perf_counter()
                image, route = self.source.get(target, 60)  # measured break-even
                ms = (time.perf_counter() - t0) * 1000
                if self.run:
                    self.run.log("batch", target, route, ms, 0.0)
            wall = time.perf_counter() - before
            if image is not None:
                self._show(image)
            self.hud.setText(
                f"batch {count} sorted in {wall:.2f} s = "
                f"{1000 * wall / count:.1f} ms/frame · compare against hop")
            self.slider.blockSignals(True)
            self.slider.setValue(self.source.pos)
            self.slider.blockSignals(False)
        finally:
            self._busy = False
            self._touch()

    # ── sweep: the graph-refill task ─────────────────────────────────────
    def _sweep(self) -> None:
        if not self.source or self._busy:
            return
        self._busy = True
        try:
            start = self.source.pos + 1
            count = min(300, self.source.nframes - start)
            if count <= 0:
                return
            before = time.perf_counter()
            image = None
            for idx in range(start, start + count):
                image, _route = self.source.get(idx, 10_000,
                                                prefer="throughput")
            wall = time.perf_counter() - before
            if image is not None:
                self._show(image)
            rate = count / wall
            if self.run:
                self.run.sweeps.append({
                    "frames": count, "wall_s": round(wall, 3),
                    "fps": round(rate, 1), "from": start,
                })
            self.hud.setText(
                f"sweep {count} frames in {wall:.2f} s = {rate:.0f} fps "
                f"({rate / self.source.fps:.1f}× realtime) · now at "
                f"{self.source.pos}")
            self.slider.blockSignals(True)
            self.slider.setValue(self.source.pos)
            self.slider.blockSignals(False)
        finally:
            self._busy = False
            self._touch()

    def _sweep_parallel(self) -> None:
        """The pipeline shape: fresh decoders take disjoint chunks at once.

        Every result so far is single-consumer; this is where that assumption
        meets the machine. Each worker opens its own container (open cost is
        part of the wall, as it would be in a real pass), seeks to a
        GOP-aligned start, and decodes 300 luma frames. The view does not
        move: a pipeline pass is not a viewing."""
        if not self.source or self._busy:
            return
        self._busy = True
        try:
            path = self.paths[self.file_box.currentIndex()]
            chunk, gop = 300, 24  # gop: alignment hint only (results/04-*)
            base = ((self.source.pos + 1) // gop + 1) * gop
            import os

            n_sw = int(self.psweep_shape.currentText()[0])
            # a lone sw worker gets full threading; siblings split whatever
            # cores this machine actually has
            cores = os.cpu_count() or 8
            threads = 0 if n_sw == 1 else max(2, cores // n_sw)
            specs = [("sw", {"luma": True, "thread_count": threads})] * n_sw
            specs += [("hw", {"luma": True, "hwaccel": "cuda"})]
            starts = [base + k * chunk for k in range(len(specs))]
            fits = [(s, st) for s, st in zip(specs, starts)
                    if st + chunk <= self.source.nframes]
            if not fits:
                self.hud.setText("∥ sweep: too close to the end of the file")
                return

            def work(spec_start):
                (kind, kwargs), start = spec_start
                t0 = time.perf_counter()
                try:
                    src = PyAVSource(path, **kwargs)
                except Exception as exc:  # noqa: BLE001 - absence is the datum
                    return {"kind": kind, "start": start, "error": str(exc)}
                try:
                    src.get(start, 0)
                    done = 1
                    for idx in range(start + 1, start + chunk):
                        src.get(idx, 10_000)
                        done += 1
                finally:
                    src.close()
                wall = time.perf_counter() - t0
                return {"kind": kind, "start": start, "frames": done,
                        "wall_s": round(wall, 3), "fps": round(done / wall, 1)}

            before = time.perf_counter()
            with ThreadPoolExecutor(max_workers=len(fits)) as pool:
                results = list(pool.map(work, fits))
            wall = time.perf_counter() - before
            ok = [r for r in results if "error" not in r]
            total = sum(r["frames"] for r in ok)
            rate = total / wall if wall else 0.0
            if self.run:
                self.run.sweeps.append({
                    "frames": total, "wall_s": round(wall, 3),
                    "fps": round(rate, 1), "parallel": results,
                })
            per_worker = ", ".join(
                f"{r['kind']} {r['fps']:.0f}" for r in ok)
            errors = "; ".join(
                f"{r['kind']}: {r['error'][:40]}" for r in results
                if "error" in r)
            self.hud.setText(
                f"∥ sweep {total}f in {wall:.2f} s = {rate:.0f} fps "
                f"({rate / self.source.fps:.1f}× realtime) · per worker: "
                f"{per_worker}" + (f" · failed: {errors}" if errors else ""))
        finally:
            self._busy = False
            self._touch()

    def _announce(self, text: str) -> None:
        self.hud.setText(text)
        self.hud.repaint()

    def _test_all(self) -> None:
        """The battery: every surviving approach through every mode.

        Exists so a session cannot miss a combination: the same scripted
        drags, forward and reverse play, hops, batch and sweep run against
        each approach on the current source, land in the same per-run logs
        as hand fiddling, and finish with one lean parallel pipeline sweep.
        Drags are exact (no kf-snap) so approaches stay comparable."""
        if self._busy or not self.paths:
            return
        self.testall_btn.setEnabled(False)
        try:
            for approach in [a for a in APPROACHES if a not in RETIRED]:
                self.approach_box.setCurrentText(approach)
                if not self.source or self.source.nframes < 2:
                    continue  # could not open; HUD said why, log notes absence
                n = self.source.nframes
                try:
                    self._announce(f"[test all] {approach} · drags")
                    for _ in range(12):
                        self.request(self._rng.randrange(n), "drag",
                                     exact=True)
                    self._announce(f"[test all] {approach} · play 100")
                    start = self._rng.randrange(max(1, n - 140))
                    self.request(start, "step", exact=True)
                    for _ in range(100):
                        nxt = self.source.pos + 1
                        if nxt >= n:
                            break
                        self.request(nxt, "play")
                    self._announce(f"[test all] {approach} · reverse 15")
                    for _ in range(15):
                        nxt = self.source.pos - 1
                        if nxt < 0:
                            break
                        self.request(nxt, "rev")
                    self._announce(f"[test all] {approach} · hop 20")
                    for _ in range(20):
                        self.request(self._rng.randrange(n), "hop")
                    self._announce(f"[test all] {approach} · batch")
                    self._batch()
                    self._announce(f"[test all] {approach} · sweep")
                    self.request(0, "step", exact=True)  # room for 300
                    self._sweep()
                except Exception as exc:  # noqa: BLE001 - one approach's
                    # failure must not abort the battery (the FFV1/MKV
                    # nframes=0 crash cost a whole run on 2026-08-21)
                    if self.run:
                        self.run.sweeps.append(
                            {"frames": 0, "wall_s": 0.0, "fps": 0.0,
                             "aborted": repr(exc)[:120]})
                    self._announce(f"[test all] {approach} aborted: {exc}")
            self._announce("[test all] parallel pipeline sweep 1sw+1hw")
            self.psweep_shape.setCurrentText("1sw+1hw")
            self._sweep_parallel()
            self._save_log()
            self._redraw_graphs()
            self.hud.setText(
                "[test all] done — graphs, stats and log hold every combination")
        finally:
            self.testall_btn.setEnabled(True)

    # ── graphs, stats, log file ──────────────────────────────────────────
    def _touch(self) -> None:
        """Schedule graph and log refresh without sitting in the request path."""
        if not self._graph_timer.isActive():
            self._graph_timer.start()
        if not self._save_timer.isActive():
            self._save_timer.start()

    def _ordered_runs(self) -> list[RunLog]:
        return [r for r in self.runs.values() if r.events or r.sweeps]

    def _redraw_graphs(self) -> None:
        if self._busy or self.play_btn.isChecked() \
                or self.rev_btn.isChecked() or self.hop_btn.isChecked():
            self._graph_timer.start(1200)  # not during the thing being felt
            return
        runs = self._ordered_runs()
        cmap = matplotlib.colormaps["tab10"]

        fig = self.trace_fig
        fig.clear()
        ax = fig.add_subplot(111)
        for index, run in enumerate(runs):
            color = cmap(index % 10)
            for task, marker in TASK_MARKERS.items():
                xs = [i for i, e in enumerate(run.events) if e["task"] == task]
                ys = [run.events[i]["ms"] for i in xs]
                if xs:
                    ax.scatter(xs, ys, s=14, marker=marker, color=color,
                               alpha=0.7,
                               label=run.label if task == "drag" or (
                                   task == "play" and not any(
                                       e["task"] == "drag" for e in run.events))
                               else None)
        if runs:
            ax.set_yscale("log")
            ax.grid(True, which="both", alpha=0.25)
            ax.legend(fontsize=7, loc="best")
        else:
            ax.set_axis_off()
        ax.set_xlabel("request # per run   (o drag · . play · ^ step · s open)")
        ax.set_ylabel("decode ms (log)")
        ax.set_title("every request this launch")
        self.trace_canvas.draw_idle()

        fig = self.compare_fig
        fig.clear()
        ax = fig.add_subplot(111)
        names, p50s, p95s, colors = [], [], [], []
        for index, run in enumerate(runs):
            summary = run.summary()
            for task, q in summary["by_task"].items():
                if task == "open":
                    continue
                names.append(f"{run.label} · {task}")
                p50s.append(q["p50"])
                p95s.append(q["p95"])
                colors.append(cmap(index % 10))
        if names:
            order = sorted(range(len(names)), key=lambda k: p50s[k])
            names = [names[k] for k in order]
            ax.barh(names, [p50s[k] for k in order], height=0.6,
                    color=[colors[k] for k in order], alpha=0.85)
            ax.scatter([p95s[k] for k in order], names, marker="|", s=160,
                       color="black", zorder=3)
            ax.set_xscale("log")
            ax.grid(True, axis="x", which="both", alpha=0.25)
            ax.tick_params(axis="y", labelsize=7)
        else:
            ax.set_axis_off()
        ax.set_xlabel("ms per request, log   (bar p50 · tick p95)")
        ax.set_title("runs compared")
        self.compare_canvas.draw_idle()

        self.stats.setPlainText("\n\n".join(r.stats_text() for r in runs))

    def _save_log(self) -> None:
        if self._busy:
            self._save_timer.start(1500)
            return
        payload = {
            "tool": "explorer.py",
            "when": datetime.now(timezone.utc).isoformat(),
            "sieve_rev": harness._sieve_rev(),
            "machine": harness._machine(),
            "versions": harness._versions(),
            "step_within": self.step_within.value(),
            "coalesce": self.coalesce.isChecked(),
            "kf_snap": self.snap.isChecked(),
            "runs": [
                {**run.summary(), "started": run.started, "events": run.events}
                for run in self._ordered_runs()
            ],
        }
        self.log_path.write_text(json.dumps(payload, indent=1),
                                 encoding="utf-8")

    def _clear_runs(self) -> None:
        self.runs.clear()
        self.run = None
        self._reopen()
        self._redraw_graphs()
        self._save_log()

    def closeEvent(self, event) -> None:
        self.play_btn.setChecked(False)
        self._save_log()
        if self.source:
            self.source.close()
        super().closeEvent(event)

    # ── keys ─────────────────────────────────────────────────────────────
    def keyPressEvent(self, event) -> None:
        if not self.source:
            return super().keyPressEvent(event)
        key = event.key()
        if key == Qt.Key.Key_Right:
            self.request(min(self.source.pos + 1, self.source.nframes - 1), "step")
        elif key == Qt.Key.Key_Left:
            self.request(max(self.source.pos - 1, 0), "step")
        elif key == Qt.Key.Key_Space:
            self.play_btn.toggle()
        else:
            super().keyPressEvent(event)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    window = Explorer()
    if "--smoke" in sys.argv:
        for i in range(window.approach_box.count()):
            window.approach_box.setCurrentIndex(i)
            if window.source:
                for frame in (5, 6, 30):
                    window.request(frame, "drag")
            print(f"{window.approach_box.currentText():<36} {window.hud.text()}")
        window._redraw_graphs()
        window._save_log()
        data = json.loads(window.log_path.read_text(encoding="utf-8"))
        print(f"smoke ok: {len(data['runs'])} runs logged to {window.log_path.name}")
        return
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
