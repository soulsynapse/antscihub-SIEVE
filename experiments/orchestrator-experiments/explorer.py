"""Feel the orchestrator: one dispatcher, ranked by pressure, sharing every decode.

Forked from `storage-experiments/session-explorer.py` and
`tool-experiments/tool-explorer.py`, rewritten so that nothing decodes
except the dispatcher, and everything that wants a frame — the GUI's drag,
the window sweep, the tool's ordered pass — says so by declaring a `Need`
through the graph. The dispatcher reads `graph.pressure_queue()` and serves
the highest-pressure row that is not on hand. That is the whole
scheduling policy, and this explorer exists to find out what it feels like.

What changed from the first version of this explorer, and why:

  full frame    `_luma` returns the whole 5312x2988 plane, not a crop. At a
                1 MB crop, declaration-derived eviction was decorative — the
                window fit whatever budget you named. At ~16 MB a frame it
                is load-bearing, and a 20 s window is the first configuration
                where a wrong hold is a wrong answer about memory rather
                than a rounding error. It is also the honest form: the crop
                is drawn at interaction time and a pool keyed to it is a
                pool the user can invalidate by dragging.

  20 s window   480 frames at 23.976 fps. The tuning loop's unit is a
                behavioural bout, not a round number of frames, so the
                window is stated in seconds and the frame count follows.

  dispatcher    one thread, one decoder, serving by pressure. The linear
                attention-first fill is gone: the sweep is now a node that
                declares its whole window in attention-first *order*, and
                the dispatcher is free to interleave the GUI ahead of it.
                Preemption granularity is one decode — 10 ms if the
                dispatcher is stepping, up to a seek if it is not — and
                that latency is what the `dispatch` route reports.

  no GUI decode the GUI declares INTERACTIVE and waits. It used to hold its
                own `Fetcher` and decode misses inline, which is a second
                decoder on the same file, which `07-contention` already
                priced. If priority scheduling works, the GUI does not need
                one; if it does need one, that is the finding.

  shared count  the pool records which node's decode produced each frame
                and counts every serve to a different node. "Decode once,
                serve many" is the claim the graph is built on, so the
                claim carries a number.

  walk / legs   the same five-leg shape the session explorer walks — hunt,
                land A cold, tune, jump to the B seam, return to A — with a
                `RunLog` per leg, so a leg here and the same-named leg
                there are read off the same axis.

One form, deliberately. Everything declares the full-frame source form and
the tool derives its crop inside its own timing envelope. Cross-form
negotiation in the pool is experiment 7 in the README, and mixing it in
here would make the shared-decode count a statement about two things.

What is still NOT here: the proxy tier, chunked write-behind, the series
writer. Each is a tier the graph does not yet schedule.

Run:
    uv run --group experiments python experiments/orchestrator-experiments/explorer.py
    ... --walk    headless, runs the five legs, writes the log, exits
    ... --walk --quick   the same five legs at a third of the scrubbing,
                  for checking the script still runs. The walls are not
                  comparable to a full walk and the log says which it was.
    ... --walk --live-playhead
                  the same legs with the loop timer left running, so each
                  window fills against a moving playhead. The A/B for what
                  per-frame preemption costs.
    ... --window-seconds N
                  shrink the window for a fast validation run. Scheduling
                  behaviour is scale-free; the memory numbers are not, and
                  the log records `window_is_full_size` so a short run
                  cannot be read as one.
    ... --smoke   headless, one window, a few frames, sanity only
"""

from __future__ import annotations

import json
import random
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import av
import cv2
import numpy as np

sys.setswitchinterval(0.002)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from harness import FOOTAGE
from graph import Envelope, Graph, Need, Urgency
from pool import Pool
import forms as forms_mod
import tools as tools_mod

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
LOGS = Path(__file__).resolve().parent / "explorer-logs"

def _argf(flag: str, default: float) -> float:
    """`--flag N` off the command line, or the default."""
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            return float(sys.argv[i + 1])
    return default


#: The window is a bout, and the frame count follows from the rate. It is a
#: knob because only ONE of the questions this explorer asks needs the real
#: size: the memory one. Seeks, stale preemptions, shared serves and the
#: seek/step ratio are all scale-free, so validating the script at 20 s
#: costs 480 decodes a window to learn what 60 costs 60 decodes to learn.
#: A run states which it used, and a memory number from a short window is
#: not a memory number.
WINDOW_SECONDS = _argf("--window-seconds", 20.0)
NEAR_RADIUS = 12         #: how far a stale frame may stand in while scrubbing
STEP_WITHIN = 60         #: beyond this a seek beats stepping (decode-exp 03)
GOP = 24
CROP_RECT = [2144, 982, 1024, 1024]   #: what the *tool* looks at, not the pool
EXACT_WAIT_S = 1.5       #: how long an exact request waits on the dispatcher
EVENT_CAP = 20_000
POOL_BUDGET = 12 << 30   #: 12 GB — a 480-frame full-frame window is ~7.6 GB

#: `--live-playhead` lets the loop-play timer keep running under every leg,
#: so the sweep fills against a moving playhead instead of an idle one. It
#: is the A/B for what per-frame preemption costs: same dispatcher, same
#: script, the only difference being whether anything is declaring
#: INTERACTIVE while the window fills.
LIVE_PLAYHEAD = "--live-playhead" in sys.argv

TASK_MARKERS = ("hunt", "drag", "scrub", "play", "step", "hop", "open")


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _luma(frame) -> np.ndarray:
    """The whole luma plane, copied out of the decoder's buffer.

    The copy is not optional. A view onto `plane` keeps the entire AVFrame
    alive — all three planes, ~24 MB for yuv420p at this size — so a pool
    of 480 views costs 11 GB to hold 7.6 GB of pixels, and the extra is
    chroma nothing in this tree reads.
    """
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    #: `.copy()`, not `ascontiguousarray`. At this width the stride equals
    #: the width, so the slice is already contiguous and
    #: `ascontiguousarray` hands back the view it was given — silently
    #: pinning the frame it was supposed to release.
    return arr.reshape(frame.height, plane.line_size)[:, : frame.width].copy()


class Fetcher:
    """One open container, absolute frame indices, sequential cursor.

    Reports how it got there. A dispatcher ranked by pressure rather than by
    row pays for every reorder in seeks, and the seek/step split is the
    price of the policy — the number that says whether priority scheduling
    is worth what locality it gave up.
    """

    def __init__(self):
        self.container = av.open(str(BIG))
        self.stream = self.container.streams.video[0]
        self.stream.thread_type = "AUTO"
        self.pts_of, self.step = _pts_helpers(self.stream)
        self._pos: int | None = None
        self._decoded = None

    def exact(self, idx: int) -> tuple[np.ndarray, str]:
        if self._decoded is not None and self._pos is not None:
            ahead = idx - self._pos
            if 0 < ahead <= STEP_WITHIN:
                try:
                    for _ in range(ahead):
                        frame = next(self._decoded)
                    self._pos = idx
                    return _luma(frame), "step"
                except StopIteration:
                    pass
        target = self.pts_of(idx)
        half = self.step / 2
        self.container.seek(target, stream=self.stream)
        self._decoded = self.container.decode(self.stream)
        for frame in self._decoded:
            if frame.pts is not None and frame.pts + half >= target:
                self._pos = idx
                return _luma(frame), "seek"
        raise RuntimeError(f"off the end at {idx}")

    def close(self) -> None:
        self.container.close()


class Dispatcher:
    """The only thing in this explorer that decodes.

    Reads the graph's pressure queue, takes the highest-pressure need with
    an unserved row, decodes that one row, puts it in the pool,
    and re-consults. Re-consulting after every single frame is what makes
    preemption granularity one decode rather than one window; it is also
    what lets a node's declared *order* (attention-first, for a sweep) win
    within a pressure band while a higher band cuts in front of it.

    It does not know what a GUI is, what a tool is, or where attention is.
    It knows a sorted list of declarations. Everything else is policy the
    nodes spelled in what they declared, which is the claim question 1 in
    the README makes and this class is the test of.
    """

    def __init__(self, graph: Graph, pool: Pool, form_key: str,
                 t0: float = 0.0):
        self._t0 = t0
        self.graph = graph
        self.pool = pool
        self.form_key = form_key
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.served = 0
        self.seeks = 0
        self.steps = 0
        self.idle_polls = 0
        self.failures = 0
        #: decodes that landed after the node asking had already moved on.
        #: The price of preempting per-frame for a consumer whose row
        #: changes faster than a seek — a scrub declares dozens of these.
        self.stale = 0
        self.by_pressure: dict[str, int] = {}
        #: every choice in order — role, row, how, cost, and how much
        #: of the window was covered when it was made. The counts say what
        #: the policy cost; only the sequence says why, because the cost of
        #: a decode is a function of the one before it.
        self.trace: list[tuple] = []
        self.trace_cap = 20_000
        self.last: str = "idle"

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=15)
        self._thread = None

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _pick(self) -> tuple[Need, int] | None:
        for need in self.graph.pressure_queue():
            if need.form_key != self.form_key:
                continue
            unserved = need.unserved(self.pool.has)
            if unserved:
                return need, unserved[0]
        return None

    def _run(self) -> None:
        fetcher = Fetcher()
        try:
            while not self._stop.is_set():
                pick = self._pick()
                if pick is None:
                    self.idle_polls += 1
                    self.last = "idle"
                    time.sleep(0.004)
                    continue
                need, idx = pick
                #: `dispatch:<role>`, not the node's own id. Attributing a
                #: decode to the node that declared it makes a duration bar
                #: claim the GUI spent 49% of the time computing, when what
                #: it spent was a seek somebody else performed on its
                #: behalf. The bars have to separate work a node did from
                #: work done for it, or they are not the five clocks.
                env = Envelope(f"dispatch:{_role(need.node_id)}", idx,
                               need.form_key, "dispatch").open()
                try:
                    arr, how = fetcher.exact(idx)
                except Exception:
                    self.failures += 1
                    #: a row nothing can decode would otherwise be
                    #: picked forever — park a None so `has` says yes
                    self.pool.put(idx, need.form_key, np.zeros((1, 1), np.uint8),
                                  by=need.node_id)
                    continue
                env.route = how
                env.close()
                self.graph.record(env)
                self.pool.put(idx, need.form_key, arr, by=need.node_id)
                self.served += 1
                if how == "seek":
                    self.seeks += 1
                else:
                    self.steps += 1
                band = f"{_role(need.node_id)}/{need.urgency.name}"
                self.by_pressure[band] = self.by_pressure.get(band, 0) + 1
                if len(self.trace) < self.trace_cap:
                    self.trace.append((round(env.t_end - self._t0, 4),
                                       _role(need.node_id), idx, how,
                                       round(env.ms, 2)))
                if not self.graph.still_wants(need.node_id, idx,
                                              need.form_key):
                    self.stale += 1
                self.last = f"{_role(need.node_id)}/{band} @{idx} {how}"
        finally:
            fetcher.close()

    def stats(self) -> dict:
        return {"served": self.served, "seeks": self.seeks,
                "steps": self.steps, "failures": self.failures,
                "stale": self.stale, "idle_polls": self.idle_polls,
                "by_pressure": dict(self.by_pressure)}


class Sweep:
    """A node that wants a whole window, in attention-first order.

    Not a thread. It declares once — every row in the window, as
    offsets rotated so the anchor comes first — and the dispatcher works
    through that order at BACKGROUND pressure whenever nothing outranks it.
    The declaration is also the hold: 480 rows in the graph's refs is
    what keeps the pool from sweeping the window out from under the tool.

    Replacing a fill thread with a declaration is the point. The old fill
    decided its own order and could not be interrupted between frames
    except by a stop flag; this one states its order and is interrupted by
    anything that declares higher pressure, which is the same thing the
    old code called "preempt" and had to implement by hand.
    """

    #: One node for the whole session, not one per landing. `declare`
    #: replaces a node's previous declaration and releases only the
    #: difference, so re-declaring onto an overlapping window keeps the
    #: overlap held for free. Minting a node per window made the overlap
    #: nobody's, and then whether it survived depended on the order two
    #: calls happened to be written in — measured at 72 decodes where 36
    #: were already in RAM.
    NODE_ID = "fill"

    def __init__(self, start: int, end: int, anchor: int,
                 form_key: str, graph: Graph):
        self.node_id = self.NODE_ID
        self.start, self.end = start, end
        self.anchor = max(start, min(anchor, end - 1))
        self.form_key = form_key
        self.graph = graph
        self.declared_at = time.perf_counter()

    def declare(self) -> None:
        span = list(range(0, self.end - self.start))
        first = self.anchor - self.start
        order = tuple(span[first:] + span[:first])
        self.graph.declare(Need(self.node_id, self.start, order,
                                self.form_key, Urgency.DEFERRED))

    def release(self) -> None:
        self.graph.release(self.node_id)


class ToolRunner:
    """A tool's ordered pass over the window, riding on the sweep's decodes.

    Declares source-form rows through the graph — the same form the
    GUI and the sweep declare — and derives its crop itself. The derivation
    is inside the envelope on purpose: it is the tool's cost, not the
    dispatcher's, and a graph that hid it would report a step as free that
    is paying 1 MB of memcpy a row.

    It declares DEFERRED and says nothing about where it ranks. It used to
    raise itself toward the playhead, which read as reasonable and was the
    measured defect: its rows sit inside the sweep's declared window,
    so outranking the sweep bought by seek what was already arriving by
    sequential read, and stalled the producer while doing it. The graph
    subsumes it now (ADR-0006, ADR-0007).
    """

    def __init__(self, tool: tools_mod.Tool, source_form: forms_mod.Form,
                 graph: Graph, pool: Pool):
        self.tool = tool
        self.source_form = source_form
        self.crop_form = tool.form_for(tuple(CROP_RECT))
        self.graph = graph
        self.pool = pool
        self.node_id = f"tool-{tool.name}-{id(self)}"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.values: dict[int, float] = {}
        self.pos: int | None = None
        self.computed = 0
        self.starved = 0     #: rows abandoned waiting on the dispatcher
        self.derive_ms = 0.0

    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def run_over(self, start: int, end: int) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._work, args=(start, end), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)
        self._thread = None
        self.graph.release(self.node_id)

    def _work(self, start: int, end: int) -> None:
        fk = self.source_form.key()
        reach = self.tool.reach
        derived: dict[int, np.ndarray] = {}

        try:
            for pos in range(start + reach, end):
                if self._stop.is_set():
                    return

                needed = self.tool.needs(pos)
                self.graph.declare(Need(self.node_id, pos, self.tool.offsets,
                                        fk, Urgency.DEFERRED))

                fulls: dict[int, np.ndarray] = {}
                deadline = time.perf_counter() + 10.0
                while len(fulls) < len(needed):
                    if self._stop.is_set():
                        return
                    for n in needed:
                        if n not in fulls:
                            arr = self.pool.get(n, fk, by=self.node_id)
                            if arr is not None:
                                fulls[n] = arr
                    if len(fulls) < len(needed):
                        if time.perf_counter() > deadline:
                            break
                        time.sleep(0.005)

                if len(fulls) < len(needed):
                    self.starved += 1
                    continue

                env = Envelope(self.node_id, pos, fk, "field").open()
                frames = {}
                for n in needed:
                    crop = derived.get(n)
                    if crop is None:
                        crop, _how = forms_mod.derive(
                            fulls[n], self.source_form, self.crop_form)
                        derived[n] = crop
                    frames[n] = crop
                field = self.tool.field(frames, pos)
                value = self.tool.reduce(field)
                env.close()
                self.graph.record(env)

                for n in list(derived):
                    if n < pos - reach:
                        derived.pop(n, None)

                self.values[pos] = value
                self.pos = pos
                self.computed += 1

                for n in needed:
                    self.graph.release_row(self.node_id, n, fk)
        finally:
            self.graph.release(self.node_id)


class RunLog:
    """Everything one leg of the session was asked to do this launch.

    Event times share the session clock, so legs plot on one axis — and the
    leg names match the session explorer's, so a `hunt` here and a `hunt`
    there are the same question asked of two schedulers.
    """

    def __init__(self, label: str, t0: float):
        self.label = label
        self.started = datetime.now(timezone.utc).isoformat()
        self._t0 = t0
        self.events: list[dict] = []
        self.walls: list[dict] = []
        self.capped = False
        self._steady = 0     #: a looping session floods tens of thousands of
        self.suppressed = 0  #: constant-cost play hits, and the cost of the
                             #: flood is what freezes the GUI — keep 1 in 8

    def log(self, task: str, frame: int, route: str, ms: float) -> None:
        if task == "play" and ms < 20                 and route.split(" ")[0] in ("held", "near", "wait"):
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

    def wall(self, what: str, wall_s: float, detail: str = "") -> None:
        self.walls.append({"t": round(time.perf_counter() - self._t0, 4),
                           "what": what, "wall_s": round(wall_s, 3),
                           "detail": detail})

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
        return {"label": self.label, "started": self.started,
                "by_task": by_task, "routes": routes, "walls": self.walls,
                "suppressed_play_hits": self.suppressed,
                "events_capped": self.capped,
                "events": self.events}

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


def _role(node_id: str) -> str:
    return node_id.split("-")[0]


class JumpSlider(QSlider):
    def mousePressEvent(self, event) -> None:
        from PySide6.QtWidgets import QStyle
        value = QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(),
            int(event.position().x()), self.width())
        self.setValue(value)
        super().mousePressEvent(event)


class OrchestratorExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("orchestrator explorer — one dispatcher, ranked")
        self.resize(1400, 860)

        with av.open(str(BIG)) as c:
            stream = c.streams.video[0]
            self.fps = float(stream.average_rate)
            self.orig_w, self.orig_h = stream.width, stream.height
            self.total = (stream.frames or int(
                stream.duration * stream.time_base * stream.average_rate))
        self.total -= GOP
        self.window_frames = round(WINDOW_SECONDS * self.fps)

        self.t0 = time.perf_counter()
        self.graph = Graph()
        self.pool = Pool(self.graph, budget_bytes=POOL_BUDGET)
        self.source_form = forms_mod.Form(
            (0, 0, self.orig_w, self.orig_h), (self.orig_w, self.orig_h),
            "gray")
        self.form_key = self.source_form.key()

        self.dispatcher = Dispatcher(self.graph, self.pool, self.form_key,
                                     self.t0)
        self.dispatcher.start()

        self.tool_a = tools_mod.absdiff()
        self.tool_d = tools_mod.dis_flow()
        self.active_tool = self.tool_a

        self.sweep: Sweep | None = None
        self.tool_runner: ToolRunner | None = None
        self.active: tuple[int, int] | None = None
        self.pos = 0
        self._busy = False
        self._queue: deque[int] = deque()
        self._recent: deque[float] = deque(maxlen=30)
        self._scrubbing = False
        self._last_image: np.ndarray | None = None
        #: where the transport thinks it is, which is NOT `self.pos` (where
        #: the last drawn frame was). Tying the two together is a spin: a
        #: tick that gets `wait` never updates `pos`, so the next tick asks
        #: for the same frame, and the loop runs at the event loop's speed
        #: rather than the video's. Measured in a real session: 20 000
        #: requests for frame 4076 in 0.5 s, which flooded the event cap and
        #: starved the dispatcher of the lock it needed to fill the window.
        self._transport = 0

        self.runs: dict[str, RunLog] = {}
        self.run: RunLog | None = None
        self._leg: str | None = None    #: set by the walk; None means derive
        self._walking = False

        LOGS.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS / f"orchestrator-{stamp}.json"

        # --- build UI ---
        self.tool_box = QComboBox()
        self.tool_box.addItems(["absdiff", "dis_flow"])
        self.tool_box.currentIndexChanged.connect(self._tool_changed)

        self.pool_label = QLabel("pool: 0")
        self.held_label = QLabel("graph holds: 0")
        self.shared_label = QLabel("shared: 0")
        self.disp_label = QLabel("dispatch: idle")
        self.bars_label = QLabel("bars: -")
        for w in (self.pool_label, self.held_label, self.shared_label,
                  self.disp_label, self.bars_label):
            w.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 9pt;")

        self.window_btn = QPushButton("window here")
        self.window_btn.clicked.connect(lambda: self._land_at(self.pos))
        self.play_btn = QPushButton("play")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(self._toggle_play)
        self.pause_btn = QPushButton("pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._toggle_pause)
        self.walk_btn = QPushButton("walk session")
        self.walk_btn.setToolTip(
            "Hunt, land window A cold, tune the tool over it, jump to the B "
            "seam, return to A. Every leg lands in the log as its own "
            "RunLog, on the same clock, under the same names the session "
            "explorer uses.")
        self.walk_btn.clicked.connect(self._walk)

        row1 = QHBoxLayout()
        for w in (QLabel("tool:"), self.tool_box, self.window_btn,
                  self.play_btn, self.pause_btn, self.walk_btn):
            row1.addWidget(w)
        row1.addStretch(1)

        row2 = QHBoxLayout()
        for w in (self.pool_label, self.held_label, self.shared_label,
                  self.disp_label):
            row2.addWidget(w)
        row2.addStretch(1)

        row3 = QHBoxLayout()
        row3.addWidget(self.bars_label)
        row3.addStretch(1)

        self.canvas = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.canvas.setMinimumSize(320, 240)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Ignored,
                                  QSizePolicy.Policy.Ignored)
        self.canvas.setStyleSheet("background: #101010;")

        self.slider = JumpSlider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setMaximum(self.total - 1)
        self.slider.sliderMoved.connect(lambda i: self.request(i, "scrub"))
        self.slider.valueChanged.connect(lambda i: self.request(i, "scrub"))
        self.slider.sliderPressed.connect(self._scrub_began)
        self.slider.sliderReleased.connect(self._released)

        self.hud = QLabel("cold — drag, click 'window here', or walk")
        self.hud.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10pt; padding: 3px;")
        self.hud.setSizePolicy(QSizePolicy.Policy.Ignored,
                               QSizePolicy.Policy.Fixed)

        self.coverage_label = QLabel("")
        self.coverage_label.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 8pt; color: #6a6;")
        self.coverage_label.setSizePolicy(QSizePolicy.Policy.Ignored,
                                          QSizePolicy.Policy.Fixed)

        self.timing_text = QLabel("")
        self.timing_text.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 9pt; color: #aaa;"
            "padding: 4px;")
        self.timing_text.setWordWrap(True)
        self.timing_text.setSizePolicy(QSizePolicy.Policy.Ignored,
                                       QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout()
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.slider)
        layout.addWidget(self.coverage_label)
        layout.addWidget(self.hud)
        layout.addWidget(self.timing_text)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._play_tick)

        self._hud_timer = QTimer(self, interval=500)
        self._hud_timer.timeout.connect(self._refresh_status)
        self._hud_timer.start()

        self._save_timer = QTimer(self, singleShot=True, interval=5000)
        self._save_timer.timeout.connect(self._save_log)

        self._landed_at = self.t0
        self._covered_wall: float | None = None
        self.request(0, "open", exact=True)

    # ── run bookkeeping ──────────────────────────────────────────────────

    def _label_for(self, idx: int) -> str:
        if self._leg is not None:
            return self._leg
        if self._in_window(idx):
            return (f"window@{self.active[0]} "
                    f"w={self.window_frames} tool={self.active_tool.name}")
        return "hunt"

    def _run_for(self, idx: int) -> RunLog:
        label = self._label_for(idx)
        if label not in self.runs:
            self.runs[label] = RunLog(label, self.t0)
        self.run = self.runs[label]
        return self.run

    # ── serve ────────────────────────────────────────────────────────────

    def _serve(self, idx: int, exact: bool) -> tuple[np.ndarray | None, str]:
        """Declare, then read. The GUI never decodes — if it is not on hand,
        the dispatcher is the only thing that can produce it, and what the
        GUI does is raise the pressure and wait."""
        fk = self.form_key
        self.graph.declare(Need("gui", idx, (0,), fk, Urgency.INTERACTIVE))

        held = self.pool.get(idx, fk, by="gui")
        if held is not None:
            return held, "held"

        if not exact:
            near = self.pool.nearest(idx, fk, NEAR_RADIUS)
            if near is not None:
                best_pos, frame = near
                return frame, f"near d{idx - best_pos}"
            return None, "wait"

        t0 = time.perf_counter()
        while time.perf_counter() - t0 < EXACT_WAIT_S:
            held = self.pool.get(idx, fk, by="gui")
            if held is not None:
                waited = (time.perf_counter() - t0) * 1000
                return held, f"dispatch {waited:.0f}ms"
            QApplication.processEvents()
            time.sleep(0.002)
        return None, "timeout"

    def request(self, idx: int, task: str = "step",
                exact: bool = False) -> None:
        idx = max(0, min(self.total - 1, idx))
        self._queue.clear()
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
                    image, route = self._serve(target, exact)
                    ms = (time.perf_counter() - before) * 1000
                except Exception as exc:
                    self.hud.setText(f"frame {target}: {exc}")
                    continue
                run.log(task, target, route, ms)
                if image is None:
                    continue
                self.pos = target
                self._transport = target
                self._show(image)
                self._recent.append(ms)
                mean = sum(self._recent) / len(self._recent)
                self.hud.setText(
                    f"frame {target:>6} . {task:<5} . {route:<14}"
                    f" . {ms:7.1f} ms . last {len(self._recent)} mean "
                    f"{mean:6.1f} ms")
                self.slider.blockSignals(True)
                self.slider.setValue(target)
                self.slider.blockSignals(False)
                QApplication.processEvents()
        finally:
            self._busy = False
            if not self._save_timer.isActive():
                self._save_timer.start()

    # ── display ──────────────────────────────────────────────────────────

    def _show(self, image: np.ndarray) -> None:
        #: the full frame is 16 MB; downscale to the canvas *before* drawing
        #: overlays, so the annotation cost is canvas-sized rather than
        #: source-sized. Drawing at source and letting Qt scale was 40 ms a
        #: frame here, which is the whole interactive budget.
        cw = max(320, self.canvas.width())
        scale = min(1.0, cw / image.shape[1])
        if scale < 1.0:
            display = cv2.resize(
                image, (round(image.shape[1] * scale),
                        round(image.shape[0] * scale)),
                interpolation=cv2.INTER_AREA)
        else:
            display = image.copy()
        self._last_image = image

        fs = max(0.4, display.shape[1] / 1200)
        secs = self.pos / self.fps
        tc = f"{int(secs // 60)}:{secs % 60:04.1f}  f{self.pos}"
        (tw, th), _ = cv2.getTextSize(tc, cv2.FONT_HERSHEY_SIMPLEX, fs, 1)
        org = (display.shape[1] - tw - round(12 * fs), th + round(10 * fs))
        _stamp(display, tc, org, fs)

        #: the crop the *tool* reads, drawn at display scale — the pool is
        #: full-frame, so this rect is the tool's declaration made visible
        #: rather than a boundary anything stored respects
        x, y, w, h = CROP_RECT
        cv2.rectangle(display, (round(x * scale), round(y * scale)),
                      (round((x + w) * scale), round((y + h) * scale)),
                      255, max(1, round(display.shape[1] / 700)))

        pitch = round(30 * fs)
        for i, text in enumerate(self._overlay_lines()):
            _stamp(display, text, (round(12 * fs), pitch * (i + 1)), fs * 0.8)

        h_, w_ = display.shape[:2]
        qimage = QImage(display.data, w_, h_, display.strides[0],
                        QImage.Format.Format_Grayscale8)
        self.canvas.setPixmap(QPixmap.fromImage(qimage).scaled(
            self.canvas.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation))
        self.canvas.repaint()

    def _overlay_lines(self) -> list[str]:
        lines = []
        if self.active is not None:
            cov = len(self.pool.covered(*self.active, self.form_key))
            span = self.active[1] - self.active[0]
            lines.append(f"WINDOW {cov}/{span}  ({WINDOW_SECONDS:.0f}s)")
        if self.tool_runner and self.tool_runner.running():
            lines.append(f"TOOL {self.active_tool.name} "
                         f"computed={self.tool_runner.computed}")
        lines.append(f"DISPATCH {self.dispatcher.last}")
        line = (f"POOL {len(self.pool)}f "
                f"{self.pool.nbytes / (1 << 30):.2f}GB  "
                f"shared={self.pool.shared}")
        if self.pool.predicted:
            line += f"  PREDICTED REFETCH {self.pool.predicted}"
        lines.append(line)
        return lines

    # ── window ───────────────────────────────────────────────────────────

    def _land_at(self, pos: int) -> None:
        start = max(0, min(pos, self.total - self.window_frames))
        end = min(start + self.window_frames, self.total)
        if self.tool_runner:
            self.tool_runner.stop()
        self.active = (start, end)
        self._transport = pos

        #: one node re-declaring, so the overlap between two windows is
        #: never unheld and there is no order to get wrong
        self.sweep = Sweep(start, end, pos, self.form_key, self.graph)
        self.sweep.declare()
        self.graph.clear_timings()
        self.pool.sweep()
        self._landed_at = self.sweep.declared_at
        self._covered_wall = None

        self.tool_runner = ToolRunner(
            self.active_tool, self.source_form, self.graph, self.pool)
        self.tool_runner.run_over(start, end)

        self._scrubbing = False
        #: the walk scripts the playhead; letting `_land_at` also start the
        #: loop timer puts an unscripted third consumer in the pressure
        #: queue, and it preempts the sweep into a seek on every tick. That
        #: is a real GUI behaviour and belongs in a leg that *asks* for it,
        #: not underneath every leg — it swung leg 2 from 7 s to 33 s
        #: between two runs of the identical script.
        self.pause_btn.setChecked(self._walking and not LIVE_PLAYHEAD)
        self._drive()
        self.hud.setText(
            f"window @{start} ({end - start} frames): the dispatcher fills "
            f"it whenever nothing outranks it")

    def _check_covered(self) -> None:
        """Has the active window filled? Asked from the status timer, on the
        Qt thread, because a watcher thread racing `_land_at` loses: the
        walk polls coverage itself and moves to the next leg the instant it
        is full, and a watcher that then reads a changed `self.active`
        exits without ever emitting — a wall silently missing from one leg
        and present in its neighbours, which reads as a slow leg."""
        if self.active is None or self._covered_wall is not None:
            return
        start, end = self.active
        if len(self.pool.covered(start, end, self.form_key)) < end - start:
            return
        wall = time.perf_counter() - self._landed_at
        self._covered_wall = wall
        self._window_covered(start, wall, end - start)

    def _window_covered(self, start: int, wall: float, filled: int) -> None:
        if self.run is not None:
            self.run.wall("window covered", wall,
                          f"{filled} frames @{start}, "
                          f"{self.dispatcher.seeks} seeks / "
                          f"{self.dispatcher.steps} steps / "
                          f"{self.dispatcher.stale} stale")
        self.hud.setText(f"window @{start} covered in {wall:.2f}s "
                         f"({filled} frames)")

    # ── transport ────────────────────────────────────────────────────────

    def _mode(self) -> str:
        if self.pause_btn.isChecked():
            return "paused"
        if self._scrubbing:
            return "scrub"
        if self.play_btn.isChecked():
            return "play"
        return "loop" if self.active else "idle"

    def _toggle_pause(self, on: bool) -> None:
        if on:
            self.play_btn.setChecked(False)
        self._drive()

    def _toggle_play(self, on: bool) -> None:
        if on:
            self.pause_btn.setChecked(False)
        self._drive()

    def _scrub_began(self) -> None:
        self._scrubbing = True
        self._drive()

    def _released(self) -> None:
        self._scrubbing = False
        value = self.slider.value()
        self.request(value, "drag", exact=True)
        if not self._in_window(value):
            self._land_at(value)
        self._drive()

    def _drive(self) -> None:
        mode = self._mode()
        if mode in ("paused", "scrub", "idle"):
            self._play_timer.stop()
            return
        #: both modes at the frame period. `play` used to run at 0 ms —
        #: "as fast as possible" — which measures how fast Qt can dispatch
        #: a timer, and the product constraint is stated against the video's
        #: rate, so that is the rate to serve at.
        self._play_timer.start(max(1, round(1000 / self.fps)))

    def _play_tick(self) -> None:
        if self._busy:
            return
        mode = self._mode()
        if mode not in ("loop", "play"):
            self._play_timer.stop()
            return
        nxt = self._transport + 1
        if mode == "loop" and not self._in_window(nxt):
            nxt = self.active[0]
        elif mode == "play" and nxt >= self.total:
            self.play_btn.setChecked(False)
            return
        #: advance first, serve second. A frame the dispatcher has not
        #: reached yet is a dropped frame, which is what playback does;
        #: it is not a reason to ask for it again.
        self._transport = nxt
        self.request(nxt, "play")

    def _in_window(self, idx: int) -> bool:
        return self.active is not None and self.active[0] <= idx < self.active[1]

    # ── tool switching ───────────────────────────────────────────────────

    def _tool_changed(self, index: int) -> None:
        self.active_tool = self.tool_a if index == 0 else self.tool_d
        if self.active is None:
            return
        if self.tool_runner:
            self.tool_runner.stop()
        self.graph.clear_timings()
        self.tool_runner = ToolRunner(
            self.active_tool, self.source_form, self.graph, self.pool)
        self.tool_runner.run_over(*self.active)

    # ── the walk: the whole session, scripted ────────────────────────────

    def _announce(self, text: str) -> None:
        self.hud.setText(text)
        self.hud.repaint()
        QApplication.processEvents()

    def _walk_scrub(self, n: int, seed: int, pace_s: float = 0.03) -> None:
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

    def _walk_wait_covered(self, timeout_s: float = 180.0) -> bool:
        if self.active is None:
            return False
        lo, hi = self.active
        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            if len(self.pool.covered(lo, hi, self.form_key)) >= hi - lo:
                #: the walk moves to the next leg the moment this returns,
                #: so record the wall here rather than leaving it to the
                #: status timer, which may not fire before `active` changes
                self._check_covered()
                return True
            QApplication.processEvents()
            time.sleep(0.05)
        return len(self.pool.covered(lo, hi, self.form_key)) >= hi - lo

    def _walk_wait_tool(self, timeout_s: float = 120.0) -> None:
        deadline = time.perf_counter() + timeout_s
        while (self.tool_runner is not None and self.tool_runner.running()
               and time.perf_counter() < deadline):
            QApplication.processEvents()
            time.sleep(0.05)

    def _walk(self) -> None:
        """The five legs, same shape and same names as the session
        explorer's walk. What differs is only what schedules them, which is
        the point: a leg here and a leg there are comparable because the
        script is."""
        if self._busy:
            return
        self.walk_btn.setEnabled(False)
        self._walking = True
        quick = "--quick" in sys.argv
        n = (lambda k: max(8, k // 3)) if quick else (lambda k: k)
        pace = 0.008 if quick else 0.03
        rng = random.Random(11)
        try:
            # leg 1: hunt — no window, every jump a cold seek at INTERACTIVE
            self._leg = "leg1 hunt"
            self._announce("[walk] hunting with no window — every jump is a "
                           "seek the dispatcher has to be interrupted for")
            for idx in [rng.randrange(self.total) for _ in range(n(12))]:
                self.request(idx, "hunt", exact=True)
                QApplication.processEvents()
                time.sleep(0.05)

            # leg 2: land window A cold and scrub it while it fills
            a = self.total // 3
            self._leg = "leg2 window A cold"
            self._announce("[walk] landing window A — scrubbing while the "
                           "dispatcher fills: near serves, then held")
            self._land_at(a)
            self._walk_scrub(n(60), 7, pace)
            if not self._walk_wait_covered():
                self._announce("[walk] window A never covered; stopping")
                return
            self._walk_scrub(n(30), 8, pace)

            # leg 3: tune — swap the tool over the window already in RAM
            self._leg = "leg3 tune over A"
            self._announce("[walk] tuning: absdiff -> dis over the same "
                           "window — every input is a shared serve, no decode")
            before = self.pool.decodes
            self.tool_box.setCurrentIndex(1)
            self._walk_wait_tool()
            self._walk_scrub(n(30), 12, pace)
            if self.run is not None:
                self.run.wall("tool swap", 0.0,
                              f"{self.pool.decodes - before} new decodes, "
                              f"{self.pool.shared} shared serves total")

            # leg 4: jump far to window B while A's tool still runs
            b = min(2 * self.total // 3, self.total - self.window_frames)
            self._leg = "leg4 window B seam"
            self._announce("[walk] jumping to window B — the seam: A's holds "
                           "release, B's declaration outranks nothing yet")
            self._land_at(b)
            self._walk_scrub(n(50), 9, pace)
            if not self._walk_wait_covered():
                self._announce("[walk] window B never covered; stopping")
                return

            # leg 5: return to A — what survived the graph's eviction
            self._leg = "leg5 A revisited"
            self._announce("[walk] returning to A — the graph released it "
                           "when B declared, so this is a cold refill")
            self._land_at(a)
            self._walk_scrub(n(40), 10, pace)
            self._walk_wait_covered()
            for _ in range(n(25)):
                self.request(rng.randrange(*self.active), "hop", exact=True)
                QApplication.processEvents()
                time.sleep(0.02)

            self._leg = None
            self._save_log()
            self._announce(
                f"[walk] done — {len(self.runs)} legs logged; "
                f"{self.pool.decodes} decodes, {self.pool.shared} shared, "
                f"{self.dispatcher.seeks} seeks / {self.dispatcher.steps} "
                f"steps / {self.dispatcher.stale} stale")
        finally:
            self._leg = None
            self._walking = False
            self.walk_btn.setEnabled(True)

    # ── status / timing ─────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        self._check_covered()
        self.pool_label.setText(
            f"pool: {len(self.pool)}f {self.pool.nbytes / (1 << 30):.2f}GB")
        self.held_label.setText(f"graph holds: {len(self.graph.held())}")
        pairs = "  ".join(f"{k}={v}"
                          for k, v in sorted(self.pool.shared_pairs.items()))
        self.shared_label.setText(
            f"shared: {self.pool.shared} / {self.pool.decodes} decodes"
            + (f"  refetch={self.pool.refetched}"
               f"({self.pool.predicted} predicted)"
               if self.pool.refetched else "")
            + (f"  [{pairs}]" if pairs else ""))
        d = self.dispatcher
        self.disp_label.setText(
            f"dispatch: {d.last}  ({d.seeks} seeks / {d.steps} steps"
            f" / {d.stale} stale)")

        bars = self.graph.duration_bars()
        if bars:
            parts = []
            for nid, frac in sorted(bars.items(), key=lambda x: -x[1])[:3]:
                bar_w = round(frac * 24)
                parts.append(f"{_role(nid)}: {'#' * bar_w}"
                             f"{'.' * (24 - bar_w)} {frac * 100:5.1f}%")
            self.bars_label.setText("bars: " + "  |  ".join(parts))
        else:
            self.bars_label.setText("bars: -")

        by_node = self.graph.timings_by_node()
        if by_node:
            lines = ["timing breakdown (graph envelopes):"]
            for nid, envs in sorted(by_node.items()):
                total_ms = sum(e.ms for e in envs)
                n = len(envs)
                routes: dict[str, int] = {}
                for e in envs:
                    routes[e.route] = routes.get(e.route, 0) + 1
                lines.append(
                    f"  {nid}: n={n}  total={total_ms / 1000:.2f}s  "
                    f"avg={total_ms / n:.2f}ms  "
                    + " ".join(f"{k}={v}" for k, v in sorted(routes.items())))
            if self.run is not None:
                lines.append(self.run.stats_text())
            self.timing_text.setText("\n".join(lines))

        if self.active is not None:
            cov = self.pool.covered(*self.active, self.form_key)
            span = self.active[1] - self.active[0]
            tr = self.tool_runner
            self.coverage_label.setText(
                f"window [{self.active[0]}..{self.active[1]}): "
                f"{len(cov)}/{span} covered  |  "
                f"tool {self.active_tool.name} "
                f"computed={tr.computed if tr else 0} "
                f"starved={tr.starved if tr else 0}")

        if not self._busy and self._last_image is not None \
                and not self._play_timer.isActive():
            self._show(self._last_image)

    # ── save / close ─────────────────────────────────────────────────────

    def _save_log(self) -> None:
        by_node = self.graph.timings_by_node()
        timing_summary = {}
        for nid, envs in by_node.items():
            samples = [e.ms for e in envs]
            if samples:
                timing_summary[nid] = {"n": len(samples),
                                       **harness.quantiles(samples)}
        payload = {
            "tool": "orchestrator-explorer",
            "when": datetime.now(timezone.utc).isoformat(),
            "sieve_rev": harness._sieve_rev(),
            "machine": harness._machine(),
            "versions": harness._versions(),
            "topology": {
                "nodes": ["gui", "fill (sweep)", "tool"],
                "edges": "source -> pool -> {gui, tool}",
                "form": self.form_key,
                "policy": "single dispatcher, pressure-ranked, "
                          "preempt granularity one decode",
                "walk": "quick" if "--quick" in sys.argv else "full",
                "window_is_full_size": WINDOW_SECONDS >= 20.0,
                "playhead": "live" if LIVE_PLAYHEAD else "parked",
            },
            "total_frames": self.total,
            "fps": self.fps,
            "window_seconds": WINDOW_SECONDS,
            "window_frames": self.window_frames,
            "tool_crop": list(CROP_RECT),
            "active_tool": self.active_tool.name,
            "pool": self.pool.stats(),
            "dispatcher": self.dispatcher.stats(),
            "dispatch_trace": self.dispatcher.trace,
            "graph_holds": len(self.graph.held()),
            "duration_bars": self.graph.duration_bars(),
            "timing_by_node": timing_summary,
            #: an empty leg is a bucket `_run_for` opened and nothing was
            #: served into — noise in a file whose point is comparing legs
            "runs": [r.summary() for r in self.runs.values() if r.events],
        }
        self.log_path.write_text(json.dumps(payload, indent=1),
                                 encoding="utf-8")

    def closeEvent(self, event) -> None:
        self.play_btn.setChecked(False)
        self._play_timer.stop()
        if self.tool_runner:
            self.tool_runner.stop()
        if self.sweep:
            self.sweep.release()
        self.dispatcher.stop()
        self._save_log()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Right, Qt.Key.Key_Left):
            self.pause_btn.setChecked(True)
            step = 1 if key == Qt.Key.Key_Right else -1
            self.request(self.pos + step, "step", exact=True)
        elif key == Qt.Key.Key_Space:
            self.pause_btn.toggle()
        else:
            super().keyPressEvent(event)


def _stamp(img: np.ndarray, text: str, org, fs: float) -> None:
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, fs, 0,
                max(2, round(3 * fs)), cv2.LINE_AA)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, fs, 255,
                max(1, round(1.2 * fs)), cv2.LINE_AA)


def _teardown(w: OrchestratorExplorer) -> None:
    if w.tool_runner:
        w.tool_runner.stop()
    if w.sweep:
        w.sweep.release()
    w.dispatcher.stop()


def main() -> None:
    if not BIG.exists():
        print(f"missing {BIG}")
        return

    headless = "--walk" in sys.argv or "--smoke" in sys.argv
    if headless:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    app = QApplication.instance() or QApplication(sys.argv)

    if "--smoke" in sys.argv:
        w = OrchestratorExplorer()
        w.request(100, "hunt", exact=True)
        print(w.hud.text())
        w._land_at(500)
        deadline = time.perf_counter() + 25
        while (time.perf_counter() < deadline
               and len(w.pool.covered(500, 500 + w.window_frames,
                                      w.form_key)) < 60):
            QApplication.processEvents()
            time.sleep(0.05)
        w.request(510, "scrub")
        print(w.hud.text())
        print("pool:", w.pool.stats())
        print("dispatcher:", w.dispatcher.stats())
        print("graph holds:", len(w.graph.held()))
        print("bars:", w.graph.duration_bars())
        w._save_log()
        print(f"smoke ok: log at {w.log_path.name}")
        _teardown(w)
        return

    if "--walk" in sys.argv:
        w = OrchestratorExplorer()
        w._walk()
        _teardown(w)
        w._save_log()
        data = json.loads(w.log_path.read_text(encoding="utf-8"))
        for r in data["runs"]:
            print(f"--- {r['label']}")
            for task, q in r["by_task"].items():
                print(f"    {task:<6} n={q['n']:<5} p50={q['p50']:>8.1f}"
                      f"  p95={q['p95']:>8.1f}  max={q['max']:>8.1f} ms")
            print("    routes:", r["routes"])
            for wall in r["walls"]:
                print(f"    {wall['what']}: {wall['wall_s']}s "
                      f"({wall['detail']})")
        print("pool:", data["pool"])
        print("dispatcher:", data["dispatcher"])
        print(f"walk ok: {len(data['runs'])} legs -> {w.log_path.name}")
        return

    window = OrchestratorExplorer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
