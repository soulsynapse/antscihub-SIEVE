"""Feel the activation model: nothing polls, and the GUI is a node like any other.

V2's driven session, forked from `orchestrator-experiments/explorer.py` and
walking the same five legs under the same names, so a leg here and a leg there
are read off one axis. That comparability is the point and the obligation:
V1 retires when this reproduces its numbers leg for leg, and not before.

What is different, and it is the whole folder:

  no polling      V1 had three loops asking "is it here yet" — a tool thread
                  at 5 ms with a ten-second deadline, the dispatcher at 4 ms
                  when nothing was pickable, and *the Qt thread itself* at
                  2 ms inside `_serve`, pumping events while it waited for a
                  frame. All three are gone. The Qt thread issues an
                  activation and returns; the frame arrives later on a
                  recorder thread and crosses back by queued signal.

  the GUI is a node
                  `want(row)` declares INTERACTIVE and returns immediately.
                  It does not decode, does not wait, and does not know
                  whether the row is resident. Superseding is free and
                  counted: a drag issues an activation per tick and the
                  overtaken ones are cancelled before they are re-entered
                  rather than decoded and discarded after.

  the tool is not a thread
                  `nodes.Pass` drives rows at a bounded request depth and
                  advances from whichever recorder thread finished the last
                  one. There is no `ToolRunner`, no `starved` counter, and no
                  deadline to exceed.

**A recorder thread may not touch a widget.** Everything that crosses from a
recorder to the Qt thread goes through `frameReady`, a queued signal, and the
painting happens in the slot. A direct call would work most of the time and
crash under a resize, which is the worst failure mode available.

Run:
    uv run --group tools --group experiments python experiments/orchestrator2-experiments/explorer.py
    ... --walk         the five legs, then write the log and exit
    ... --readers N    cursors. 1 is V1's shape; above 1 the bands partition
    ... --live-playhead
                       leave the transport running through every leg, so each
                       window fills against a moving playhead. The A/B for
                       what an interactive consumer costs a fill, and the
                       condition a reader-count comparison has to be run in
    ... --window-seconds N
                       shrink the window for a fast validation run. Scheduling
                       is scale-free; the memory numbers are not, and the log
                       records `window_is_full_size` so a short run cannot be
                       read as one.
    ... --smoke        headless-ish sanity: one window, a few frames, exit
"""

from __future__ import annotations

import json
import random
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import av
import cv2
import numpy as np

sys.setswitchinterval(0.002)
from PySide6.QtCore import Qt, QTimer, Signal
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

import forms as forms_mod
import tools as tools_mod
from dispatcher import Dispatcher, Reason
from fetch import Fetcher
from graph import Graph, Urgency
from nodes import Pass, StepNode, Sweep
from pool import Pool

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
LOGS = Path(__file__).resolve().parent / "explorer-logs"


def _argf(flag: str, default: float) -> float:
    if flag in sys.argv:
        index = sys.argv.index(flag)
        if index + 1 < len(sys.argv):
            return float(sys.argv[index + 1])
    return default


WINDOW_SECONDS = _argf("--window-seconds", 20.0)
READERS = int(_argf("--readers", 1))
DEPTH = int(_argf("--depth", 1))
GOP = 24
CROP_RECT = [2144, 982, 1024, 1024]
POOL_BUDGET = 12 << 30
NEAR_RADIUS = 12
EVENT_CAP = 20_000
WALK = "--walk" in sys.argv
#: keep unpinned frames until the byte ceiling forces a choice, instead of
#: discarding them at every landing. Off by default because discarding is
#: what V1 did, and leg-for-leg comparability is what this explorer is for;
#: `04-victim-cache.py` is where the choice was measured.
KEEP_VICTIMS = "--keep-victims" in sys.argv
#: leave the loop timer running through every leg, so each window fills
#: against a moving playhead instead of an idle one. V1's flag of the same
#: name and the same purpose: it is the A/B for what an interactive consumer
#: costs a fill, and without it the walk scrubs and *then* waits for
#: coverage, so the hand is idle for exactly the stretch being timed. A
#: reader-count comparison run without this measures nothing, because there
#: is nothing for the second cursor to overlap with.
LIVE_PLAYHEAD = "--live-playhead" in sys.argv
SMOKE = "--smoke" in sys.argv
QUICK = "--quick" in sys.argv


class RunLog:
    """Everything one leg was asked to do. Same shape and names as V1's, so a
    leg here and the same-named leg there plot on one axis."""

    def __init__(self, label: str, t0: float) -> None:
        self.label = label
        self.t0 = t0
        self.events: list[dict] = []
        self.walls: list[dict] = []
        self.capped = False

    def log(self, task: str, frame: int, route: str, ms: float) -> None:
        if len(self.events) >= EVENT_CAP:
            self.capped = True
            return
        self.events.append({"t": round(time.perf_counter() - self.t0, 4),
                            "task": task, "frame": frame, "route": route,
                            "ms": round(ms, 2)})

    def wall(self, what: str, wall_s: float, detail: str = "") -> None:
        self.walls.append({"t": round(time.perf_counter() - self.t0, 4),
                           "what": what, "wall_s": round(wall_s, 3),
                           "detail": detail})

    def summary(self) -> dict:
        by_task: dict[str, list[float]] = {}
        for event in self.events:
            by_task.setdefault(event["task"], []).append(event["ms"])
        out = {}
        for task, samples in by_task.items():
            ordered = sorted(samples)
            out[task] = {"n": len(ordered),
                         "p50": round(ordered[len(ordered) // 2], 2),
                         "p95": round(ordered[int(len(ordered) * 0.95)], 2)}
        return {"label": self.label, "events_capped": self.capped,
                "by_task": out, "walls": self.walls,
                "events": self.events}


class JumpSlider(QSlider):
    def mousePressEvent(self, event) -> None:
        span = max(1, self.width())
        value = self.minimum() + round(
            (self.maximum() - self.minimum()) * event.position().x() / span)
        self.setValue(int(value))
        self.sliderPressed.emit()
        super().mousePressEvent(event)


class Explorer(QMainWindow):
    #: the only way a recorder thread reaches the GUI. Queued by default
    #: across threads, which is what makes painting happen on the Qt thread.
    frameReady = Signal(int, object, float, str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("orchestrator2 — re-entrant, nothing polls")
        self.resize(1400, 860)

        with av.open(str(BIG)) as container:
            stream = container.streams.video[0]
            self.fps = float(stream.average_rate)
            self.orig_w, self.orig_h = stream.width, stream.height
            self.total = stream.frames or int(
                stream.duration * stream.time_base * stream.average_rate)
        self.total -= GOP
        self.window_frames = round(WINDOW_SECONDS * self.fps)

        self.t0 = time.perf_counter()
        self.graph = Graph()
        self.pool = Pool(self.graph, budget_bytes=POOL_BUDGET)
        self.source_form = forms_mod.Form(
            (0, 0, self.orig_w, self.orig_h), (self.orig_w, self.orig_h),
            "gray")
        self.form_key = self.source_form.key()
        self.dispatcher = Dispatcher(
            self.graph, self.pool, self.form_key, lambda: Fetcher(BIG),
            recorders=2, readers=READERS, t0=self.t0)
        self.dispatcher.start()

        self.tool_a = tools_mod.absdiff()
        self.tool_d = tools_mod.dis_flow()
        self.active_tool = self.tool_a

        self.sweep: Sweep | None = None
        self.step: StepNode | None = None
        self.step_pass: Pass | None = None
        self.active: tuple[int, int] | None = None
        self.pos = 0
        self._transport = 0
        self._scrubbing = False
        self._last_task = ""
        self.near_serves = 0
        self._paint_ms: list[float] = []
        self._recent: deque[float] = deque(maxlen=30)
        self._last_image: np.ndarray | None = None
        self._landed_at = self.t0
        self._covered_wall: float | None = None

        self.runs: dict[str, RunLog] = {}
        self.run: RunLog | None = None
        self._leg: str | None = None
        self._walking = False

        LOGS.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS / f"orchestrator2-{stamp}.json"

        self.frameReady.connect(self._on_frame)
        self._build_ui()

        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._play_tick)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._refresh_status)
        self._status_timer.start(250)
        #: **A hand-driven session used to leave nothing behind.** `_save_log`
        #: ran only from the walk and from `--smoke`, so closing a window you
        #: had been driving wrote no log at all — and the rule for this folder
        #: is that the log is ground truth for how it felt. A felt report with
        #: no log is unfalsifiable, which is the state the first one arrived
        #: in. Saved on a timer and again on close.
        self._autosave = QTimer(self)
        self._autosave.timeout.connect(lambda: self._save_log(quiet=True))
        self._autosave.start(10_000)

    # ── ui ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.tool_box = QComboBox()
        self.tool_box.addItems(["absdiff", "dis_flow"])
        self.tool_box.currentIndexChanged.connect(self._tool_changed)

        self.pool_label = QLabel("pool: 0")
        self.held_label = QLabel("graph holds: 0")
        self.disp_label = QLabel("dispatch: idle")
        self.act_label = QLabel("activations: 0")
        for widget in (self.pool_label, self.held_label, self.disp_label,
                       self.act_label):
            widget.setStyleSheet(
                "font-family: Consolas, monospace; font-size: 9pt;")

        self.window_btn = QPushButton("window here")
        self.window_btn.clicked.connect(lambda: self._land_at(self.pos))
        self.play_btn = QPushButton("play")
        self.play_btn.setCheckable(True)
        self.play_btn.toggled.connect(lambda _: self._drive())
        self.walk_btn = QPushButton("walk session")
        self.walk_btn.clicked.connect(self._walk)

        row1 = QHBoxLayout()
        for widget in (QLabel("tool:"), self.tool_box, self.window_btn,
                       self.play_btn, self.walk_btn):
            row1.addWidget(widget)
        row1.addStretch(1)

        row2 = QHBoxLayout()
        for widget in (self.pool_label, self.held_label, self.disp_label,
                       self.act_label):
            row2.addWidget(widget)
        row2.addStretch(1)

        self.canvas = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.canvas.setMinimumSize(320, 240)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Ignored,
                                  QSizePolicy.Policy.Ignored)
        self.canvas.setStyleSheet("background: #101010;")

        self.slider = JumpSlider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.slider.setMaximum(self.total - 1)
        #: `sliderMoved` only. `valueChanged` fires for the same drag *and*
        #: for a keyboard step and a programmatic set, so connecting both
        #: doubled every drag event; `_on_frame` already blocks signals when
        #: it moves the handle to follow the frame that landed.
        self.slider.sliderMoved.connect(lambda i: self.want(i, "scrub"))
        self.slider.sliderPressed.connect(self._scrub_began)
        self.slider.sliderReleased.connect(self._released)

        self.hud = QLabel("ready")
        self.hud.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 10pt;")

        body = QVBoxLayout()
        body.addLayout(row1)
        body.addLayout(row2)
        body.addWidget(self.canvas, 1)
        body.addWidget(self.slider)
        body.addWidget(self.hud)
        holder = QWidget()
        holder.setLayout(body)
        self.setCentralWidget(holder)

    # ── the GUI as a node ────────────────────────────────────────────────

    def want(self, row: int, task: str = "step") -> None:
        """Declare INTERACTIVE, show something now, and return.

        **This never waits.** V1's `_serve` sat here for up to 1.5 s, sleeping
        2 ms and pumping events, which is the interactive thread polling for a
        frame the fetch thread already knew it had. What replaces the waiting
        is the second half of the activation: the row lands, a recorder is
        re-entered, and the frame crosses back by signal.

        **What replaces the waiting is not nothing, and the first version of
        this made that mistake.** Not waiting is only half of what V1 did.
        The other half was `NEAR_RADIUS`: while dragging, serve the nearest
        held frame rather than the exact one, so the picture tracks the
        cursor. Without it a drag shows *nothing at all* — every tick
        supersedes the one before, a seek is some hundreds of milliseconds
        against drag events every few, so no request survives long enough to
        land and the image sits frozen until the hand stops. That reads
        exactly as lag, and it is a missing feature rather than a slow one.
        The stand-in is a dict lookup against what is already resident: no
        decode, no declaration, nothing scheduled.
        """
        row = max(0, min(self.total - 1, row))
        #: coalesce. `sliderMoved` and `valueChanged` both fire on a drag, so
        #: this used to issue two activations per pixel, each taking the
        #: graph's lock and the dispatcher's and waking the fetch thread. V1
        #: coalesced with a one-slot queue and a `_busy` flag; asking twice
        #: for the row already asked for is the same request.
        if row == self._transport and task == self._last_task:
            return
        self._transport = row
        self._last_task = task
        label = self._label_for(row)
        if label not in self.runs:
            self.runs[label] = RunLog(label, self.t0)
        self.run = self.runs[label]

        #: gated on residency, not on whether a mouse button is down. If the
        #: exact row is on hand the activation paints it within a
        #: millisecond and a stand-in would be a wasted paint; if it is not,
        #: the stand-in is the only thing that will appear for as long as a
        #: seek takes. Gating on `_scrubbing` instead — the first version —
        #: made this dead code in the walk, which sets no mouse state, so the
        #: one path a felt report is about was the one path never exercised.
        if not self.pool.has(row, self.form_key):
            self._show_near(row)
        self.dispatcher.get_frame("gui", row, self._activation_for(task),
                                  Urgency.INTERACTIVE, self.form_key,
                                  supersedes=True)

    def _show_near(self, row: int) -> None:
        """Paint the closest resident frame within `NEAR_RADIUS`, if any.

        A stand-in while the exact one is fetched, and never a substitute for
        it: the activation is still issued and still replaces this when it
        lands. Counted under its own route so a log can say how much of a
        drag the person actually saw approximately — V1 recorded 83 of these
        a run, which is how much of a scrub is carried by frames nobody asked
        for.
        """
        near = self.pool.nearest(row, self.form_key, NEAR_RADIUS)
        if near is None:
            return
        at, frame = near
        self._show(frame)
        self.near_serves += 1
        if self.run is not None:
            self.run.log(self._last_task, row, f"near d{row - at}", 0.0)

    def _activation_for(self, task: str):
        """One activation per request, closing over which task asked.

        A bound method cannot carry it: the second phase runs later, on
        another thread, by which time an attribute holding "which task" has
        been overwritten by whatever the hand did next. A scrub landing while
        a hunt was still in flight would file the hunt's latency under scrub,
        and the leg summaries are per task.
        """
        def activate(reason: Reason, ctx) -> None:
            if reason is Reason.INITIAL:
                ctx.request(ctx.row)
                return
            frame = ctx.get(ctx.row)
            #: across threads, so queued: the slot runs on the Qt thread and
            #: is the only place a widget is touched.
            self.frameReady.emit(ctx.row, frame, ctx.wait_ms, task)
            #: no release — the declaration is the hold on what is on screen,
            #: and it goes when the GUI declares somewhere else.
        return activate

    def _on_frame(self, row: int, frame: object, wait_ms: float,
                  task: str) -> None:
        painted = time.perf_counter()
        self.pos = row
        self._show(frame)
        #: what the Qt thread itself spends. Measured because the first
        #: guess at this session's lag was the paint path, and a bench put
        #: the downscale at ~2 ms — so it was not that, and the next report
        #: should not have to guess either.
        self._paint_ms.append((time.perf_counter() - painted) * 1000.0)
        self._recent.append(wait_ms)
        if self.run is not None:
            self.run.log(task, row, "activated", wait_ms)
        mean = sum(self._recent) / len(self._recent)
        self.hud.setText(
            f"frame {row:>6} . waited {wait_ms:7.1f} ms . last "
            f"{len(self._recent)} mean {mean:6.1f} ms")
        self.slider.blockSignals(True)
        self.slider.setValue(row)
        self.slider.blockSignals(False)

    def _show(self, image) -> None:
        if image is None:
            return
        self._last_image = image
        height, width = image.shape[:2]
        target = self.canvas.size()
        scale = min(target.width() / width, target.height() / height, 1.0)
        if scale < 1.0:
            image = cv2.resize(image, (max(1, int(width * scale)),
                                       max(1, int(height * scale))),
                               interpolation=cv2.INTER_AREA)
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        h, w = image.shape[:2]
        qimage = QImage(image.data, w, h, 3 * w, QImage.Format.Format_BGR888)
        self.canvas.setPixmap(QPixmap.fromImage(qimage.copy()))

    # ── windows ──────────────────────────────────────────────────────────

    def _label_for(self, row: int) -> str:
        if self._leg is not None:
            return self._leg
        if self.active and self.active[0] <= row < self.active[1]:
            return (f"window@{self.active[0]} w={self.window_frames} "
                    f"tool={self.active_tool.name}")
        return "hunt"

    def _land_at(self, row: int) -> None:
        start = max(0, min(row, self.total - self.window_frames))
        end = min(start + self.window_frames, self.total)
        if self.step_pass is not None:
            self.step_pass.stop()
        self.active = (start, end)
        self._transport = row

        #: one node re-declaring, so the overlap between two windows is never
        #: unheld and there is no order to get wrong.
        self.sweep = Sweep(start, end, row, self.form_key, self.graph)
        self.sweep.declare()
        if not KEEP_VICTIMS:
            #: **Declared before dropping, and that order is load-bearing.**
            #: The new window's overlap with the old is re-held by the
            #: declaration above, so dropping after it keeps the overlap and
            #: drops only what nothing wants. V1 measured the other order at
            #: 72 decodes where 36 were already in RAM.
            #:
            #: Dropping at all is V1's behaviour, kept so leg 5 is the cold
            #: refill its name says. `--keep-victims` lets the byte ceiling
            #: decide instead, which is the arrangement `04-victim-cache.py`
            #: measured — and which it found pays only when what survives is
            #: contiguous.
            self.pool.drop_unreferenced()
        self.graph.clear_timings()
        self._landed_at = time.perf_counter()
        self._covered_wall = None

        self.step = StepNode(self.active_tool, self.source_form,
                             tuple(CROP_RECT), self.dispatcher)
        self.step_pass = Pass(self.step, start + self.active_tool.reach, end,
                              depth=DEPTH)
        self.step_pass.run()
        #: the walk scripts the playhead; letting `_land_at` start the loop
        #: underneath every leg puts an unscripted third consumer in the
        #: pressure queue. V1 measured that swinging one leg from 7 s to 33 s
        #: between two runs of an identical script, so it belongs in a leg
        #: that asks for it and not beneath all of them.
        if LIVE_PLAYHEAD:
            self.play_btn.setChecked(True)
        self._drive()
        self.hud.setText(f"window @{start} ({end - start} frames)")

    def _check_covered(self) -> None:
        if self.active is None or self._covered_wall is not None:
            return
        start, end = self.active
        if len(self.pool.covered(start, end, self.form_key)) < end - start:
            return
        self._covered_wall = time.perf_counter() - self._landed_at
        if self.run is not None:
            self.run.wall("window covered", self._covered_wall,
                          f"{end - start} frames @{start}, "
                          f"{self.dispatcher.seeks} seeks / "
                          f"{self.dispatcher.steps} steps / "
                          f"{self.dispatcher.stale} stale")

    # ── transport ────────────────────────────────────────────────────────

    def _scrub_began(self) -> None:
        self._scrubbing = True
        self._drive()

    def _released(self) -> None:
        self._scrubbing = False
        value = self.slider.value()
        self.want(value, "drag")
        if not (self.active and self.active[0] <= value < self.active[1]):
            self._land_at(value)
        self._drive()

    def _drive(self) -> None:
        if self._scrubbing or not self.play_btn.isChecked():
            self._play_timer.stop()
            return
        self._play_timer.start(max(1, round(1000 / self.fps)))

    def _play_tick(self) -> None:
        nxt = self._transport + 1
        if self.active and nxt >= self.active[1]:
            nxt = self.active[0]
        self.want(nxt, "play")

    def _tool_changed(self, index: int) -> None:
        self.active_tool = (self.tool_a, self.tool_d)[index]
        if self.active is not None:
            start, end = self.active
            if self.step_pass is not None:
                self.step_pass.stop()
            self.step = StepNode(self.active_tool, self.source_form,
                                 tuple(CROP_RECT), self.dispatcher)
            self.step_pass = Pass(self.step,
                                  start + self.active_tool.reach, end,
                                  depth=DEPTH)
            self.step_pass.run()

    # ── status ───────────────────────────────────────────────────────────

    def _refresh_status(self) -> None:
        self._check_covered()
        stats = self.dispatcher.stats()
        pool = self.pool.stats()
        self.pool_label.setText(
            f"pool: {pool['frames']} / {pool['gb']} GB")
        self.held_label.setText(f"graph holds: {len(self.graph.held())}")
        self.disp_label.setText(
            f"dispatch: {self.dispatcher.last} | seeks {stats['seeks']} "
            f"steps {stats['steps']} stale {stats['stale']} "
            f"blocked {stats['blocked']}")
        self.act_label.setText(
            f"activations {stats['activations']} re-entered "
            f"{stats['reentries']} superseded {stats['superseded']} "
            f"expired {stats['expired_picks']} | step "
            f"{self.step.computed if self.step else 0}")

    # ── the walk ─────────────────────────────────────────────────────────

    def _wait_shown(self, row: int, timeout_s: float = 1.5) -> float:
        """Let Qt run until *row* is on screen, or give up. Returns the wait.

        This is the walk's hand, not the GUI's thread. V1 spelled the same
        pacing as `request(..., exact=True)`, which blocked *inside* the
        serve; here the serve has already returned and what waits is the
        script, which is a person looking at a frame before jumping again.
        Without it a hunt supersedes itself before any seek can land and the
        leg records nothing at all — measured, on the first walk this
        explorer ran.
        """
        started = time.perf_counter()
        while time.perf_counter() - started < timeout_s:
            QApplication.processEvents()
            if self.pos == row:
                break
            time.sleep(0.005)
        return (time.perf_counter() - started) * 1000.0

    def _wait(self, seconds: float) -> None:
        """Let Qt run. **Not a poll for a frame** — nothing here is waiting on
        the dispatcher; the walk is pacing a person's hand."""
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            QApplication.processEvents()
            time.sleep(0.005)

    def _wait_covered(self, timeout_s: float = 240.0) -> bool:
        if self.active is None:
            return False
        start, end = self.active
        deadline = time.perf_counter() + timeout_s
        while time.perf_counter() < deadline:
            if len(self.pool.covered(start, end, self.form_key)) >= end - start:
                self._check_covered()
                return True
            QApplication.processEvents()
            time.sleep(0.02)
        return False

    def _scrub(self, n: int, seed: int, pace_s: float = 0.03) -> None:
        lo, hi = self.active if self.active else (0, self.total)
        rng = random.Random(seed)
        anchor = rng.randrange(lo, hi)
        for _ in range(n):
            if rng.random() < 0.12:
                anchor = rng.randrange(lo, hi)
            self.want(max(lo, min(hi - 1, round(rng.gauss(anchor, 8)))),
                      "scrub")
            self._wait(pace_s)

    def _walk(self) -> None:
        """The five legs, same shape and names as V1's."""
        self.walk_btn.setEnabled(False)
        self._walking = True
        n = (lambda k: max(8, k // 3)) if QUICK else (lambda k: k)
        pace = 0.008 if QUICK else 0.03
        rng = random.Random(11)
        try:
            self._leg = "leg1 hunt"
            for row in [rng.randrange(self.total) for _ in range(n(12))]:
                self.want(row, "hunt")
                self._wait_shown(row)
                self._wait(0.05)

            a = self.total // 3
            self._leg = "leg2 window A cold"
            self._land_at(a)
            self._scrub(n(60), 7, pace)
            if not self._wait_covered():
                self.hud.setText("[walk] window A never covered; stopping")
                return
            self._scrub(n(30), 8, pace)

            self._leg = "leg3 tune over A"
            before = self.pool.stats()["puts"]
            self.tool_box.setCurrentIndex(1)
            self._wait(0.5)
            self._scrub(n(30), 12, pace)
            if self.run is not None:
                self.run.wall("tool swap", 0.0,
                              f"{self.pool.stats()['puts'] - before} new puts,"
                              f" {self.pool.shared} shared serves total")

            b = min(2 * self.total // 3, self.total - self.window_frames)
            self._leg = "leg4 window B seam"
            self._land_at(b)
            self._scrub(n(50), 9, pace)
            if not self._wait_covered():
                self.hud.setText("[walk] window B never covered; stopping")
                return

            self._leg = "leg5 A revisited"
            self._land_at(a)
            self._scrub(n(40), 10, pace)
            self._wait_covered()
            for _ in range(n(25)):
                row = rng.randrange(*self.active)
                self.want(row, "hop")
                self._wait_shown(row)
                self._wait(0.02)

            self._leg = None
            self._save_log()
        finally:
            self._leg = None
            self._walking = False
            self.walk_btn.setEnabled(True)
            if WALK:
                #: `--walk` is a scripted session and exits when the script
                #: ends, the way V1's does, so a run is a log rather than a
                #: window somebody has to remember to close.
                QTimer.singleShot(200, self.close)

    def _save_log(self, quiet: bool = False) -> None:
        stats = self.dispatcher.stats()
        painted = sorted(self._paint_ms)
        payload = {
            "when": datetime.now(timezone.utc).isoformat(),
            "footage": BIG.name,
            "topology": {
                "explorer": "orchestrator2",
                "window_frames": self.window_frames,
                "window_seconds": WINDOW_SECONDS,
                "window_is_full_size": WINDOW_SECONDS >= 20.0,
                "readers": READERS,
                "recorders": 2,
                "request_depth": DEPTH,
                "replacement": self.pool.policy.name,
                "drops_unreferenced_at_landing": not KEEP_VICTIMS,
                "live_playhead": LIVE_PLAYHEAD,
                "crop": CROP_RECT,
                "form": self.form_key,
                "total_rows": self.total,
                "fps": round(self.fps, 3),
                "quick": QUICK,
            },
            "dispatcher": stats,
            "pool": self.pool.stats(),
            "gui": {
                "near_serves": self.near_serves,
                "painted": len(painted),
                "paint_ms_p50": (round(painted[len(painted) // 2], 3)
                                 if painted else None),
                "paint_ms_p95": (round(painted[int(len(painted) * 0.95)], 3)
                                 if painted else None),
            },
            #: **Accurate here, unlike in V1's logs.** The derived-eviction
            #: finding documents `graph_holds` reading 1 in a V1 log because
            #: `closeEvent` released the sweep before saving; this saves
            #: while the window is live and `closeEvent` releases nothing
            #: from the graph, so the number is what was held. A reader
            #: comparing the two fields across the folders is comparing a
            #: measurement against an artefact.
            "graph_holds": len(self.graph.held()),
            "duration_bars": self.graph.duration_bars(),
            "dispatch_trace": self.dispatcher.trace,
            "legs": {label: run.summary() for label, run in self.runs.items()},
        }
        self.log_path.write_text(json.dumps(payload, indent=1),
                                 encoding="utf-8")
        if not quiet:
            self.hud.setText(f"log at {self.log_path.name}")
            print(f"[log] wrote {self.log_path}")

    def closeEvent(self, event) -> None:
        #: saved *before* anything is torn down, so the log describes the
        #: session that ran rather than its wreckage. V1's log has
        #: `graph_holds` reading 1 for the opposite order, which the
        #: derived-eviction finding documents as a gotcha rather than a
        #: measurement.
        self._save_log()
        if self.step_pass is not None:
            self.step_pass.stop()
        self.dispatcher.stop()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    window = Explorer()
    window.show()
    if SMOKE:
        window._land_at(window.total // 3)
        window._wait(3.0)
        window._save_log()
        window.close()
        return
    if WALK:
        QTimer.singleShot(400, window._walk)
        QTimer.singleShot(500, lambda: None)
    app.exec()


if __name__ == "__main__":
    main()
