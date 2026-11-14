r"""The simulations: each builds one fault on purpose with the player's own Graph and Worker, on a clip
and a store it writes under the folder it is handed, and returns what the catalogue's log then holds.
The graph is one, video, gray, work, bake, edge, then mean and pile as the chain; a fault is one
departure from HEALTHY's ways of walking it. Those that serve a bake need ffmpeg, as a bake does.
With --show the monitor is opened on the first one named and its fault repeated until it is closed.

    .venv\Scripts\python -m sieve_player.dev.simulations [name] [--show]
"""
import os
import sys
import tempfile
import time
from collections import namedtuple
from types import SimpleNamespace as Tool

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from tools import bake

from .. import document as D
from ..catalogue import Log
from ..decoder import Decoder
from ..graph import Graph
from ..ledger import Ledger
from ..machine import Watch
from ..pace import Pace
from ..report import line
from ..store import Store
from ..stream import HAND, Emitter
from ..worker import Worker
from .timeview import Window, context

ROWS, H, W = 64, 48, 64
EVERY = 4           # the chain's cadence, so a node run whole runs in every part of the range
MS = 1.0            # what work and edge each spin a row, well over the clip's decode and the folds
ROW = H * W

Seen = namedtuple("Seen", "log view context")
HOLD = 0.4          # s the GUI thread is kept from its loop in the simulations of its lateness, well past catalogue.LATE


def _spin(ms):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        pass


def _hold(seconds):
    """Holds the interpreter for about `seconds` in one call no other thread's turn breaks into."""
    t = time.perf_counter()
    sum(range(1_000_000))
    sum(range(int(1_000_000 * seconds / (time.perf_counter() - t))))


def _late(sample, interval_ms=50):
    """A timer of the GUI thread's sampling how late it fires, as window.Lateness does, which
    nothing under dev may import."""
    timer, due = QTimer(), []
    timer.setTimerType(Qt.TimerType.PreciseTimer)

    def fired():
        now = time.perf_counter()
        if due:
            sample("late", max(0.0, (now - due.pop()) * 1000), now)
        due.append(now + interval_ms / 1000)
    timer.timeout.connect(fired)
    timer.start(interval_ms)
    return timer


def _clip(path):
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    y, x = np.mgrid[:H, :W]
    for r in range(ROWS):
        f = ((x * 2 + y + 5 * r) % 180).astype(np.uint8)
        w.write(cv2.merge((f, f // 2, 255 - f)))
    w.release()
    return path


def _tools():
    """The graph's tools, made anew so a fault set on one is no other simulation's."""
    def frame(name, expects, fn):
        t = Tool(NAME=name, KIND="frame", EXPECTS=expects, PRODUCES="gray", DEFAULTS={"k": 0}, ms=0.0, far=0, hold=0.0)

        def run(frames, row, params):
            f = frames(row)
            if t.far:
                frames((row + t.far) % frames.count)
            _spin(t.ms)
            if t.hold and row == ROWS // 2:
                _hold(t.hold)
            return fn(f, params)
        t.run = run
        return t

    mean = Tool(NAME="mean", KIND="series", EXPECTS="gray", PRODUCES="signal", DEFAULTS={},
                fold=lambda f: np.array([f.mean()], np.float64),
                run=lambda s, p: {"signal": np.asarray(s.data, np.float32).reshape(len(s.data))},
                step=lambda state, row, i, p: (None, {"signal": np.float32(row[0])}))
    pile = Tool(NAME="pile", KIND="series", EXPECTS="signal", PRODUCES="signal", DEFAULTS={}, ms=0.0)

    def whole(s, p):
        _spin(pile.ms * len(s.data))
        return {"signal": np.asarray(s.data, np.float32)}
    pile.run = whole
    gray = frame("gray", "bgr", lambda f, p: f[..., 1] + np.uint8(p["k"]))
    work, edge = frame("work", "gray", lambda f, p: f), frame("edge", "gray", lambda f, p: f + np.uint8(p["k"]))
    work.ms = edge.ms = MS
    return {t.NAME: t for t in (gray, work, bake, edge, mean, pile)}


class _Run:
    """One simulation's graph, its stream, worker, ledger and log under `folder`, closed on leaving. `limits` are
    the stores', `memo_bytes` and `cache_bytes`, and `sample`, the seconds between the machine's samples."""

    def __init__(self, folder, served=False, pinned=(), **limits):
        QApplication.instance() or QApplication([])
        self.tools, self.store = _tools(), Store(os.path.join(folder, "store"))
        self.path = _clip(os.path.join(folder, "clip.avi"))
        self.doc = D.from_tools(list(self.tools.values()), self.path)
        self.doc.pinned = list(pinned)
        self.limits, self.worker, self.graph, self.dump = limits, None, None, None
        self._open(Ledger(timed=lambda: self.stream.turn("monitor", "ledger")))
        self.machine = Watch(lambda *sample: self.ledger.sample(*sample), limits.get("sample", 1.0))     # one for the run: its counters take 0.4 s to open
        if served:      # baked on one graph and served on a fresh one, so no store holds what is upstream of it
            D.land(self.doc.node("bake"), self.bake())
            self._shut()
            self._open(Ledger(timed=lambda: self.stream.turn("monitor", "ledger")))

    def _open(self, ledger):
        cache = self.limits.get("cache_bytes")
        self.stream = Emitter()
        self.graph = Graph(self.doc, Decoder(self.path, **({} if cache is None else {"cache_bytes": cache})), self.tools,
                           open_bake=self.store.open_bake, stream=self.stream, **{k: v for k, v in self.limits.items() if k == "memo_bytes"})
        self.ledger, self.log, self.pace = ledger, Log(), Pace()
        self.stream.on_event = ledger.event
        self.graph.sync()       # the plan, into the ledger
        self.worker = Worker(self.graph, every=EVERY, store=self.store)
        self.walked, self.series, self.baked = [], [], []
        self.worker.walked.connect(self.slot("walked", lambda done, n, *was: (self.walked.append((done, n)),
                                                                             self.pace.row("window", done, n, *was))))
        self.worker.seriesReady.connect(self.slot("seriesReady", lambda *a: self.series.append(a)))
        self.worker.bakeDone.connect(lambda nid, b: self.baked.append(b))
        self.worker.bakeRefused.connect(lambda nid, why: self.baked.append(RuntimeError(why)))
        self.lateness = _late(ledger.sample)    # one a graph: what opening the next keeps the GUI thread for is no lateness of a walk's

    def slot(self, name, fn):
        """`fn` as the window connects a worker signal's slot: a "slot" span on the thread it lands in."""
        stream = self.stream

        def timed(*args):
            with stream.turn("slot", name):
                return fn(*args)
        return timed

    def wait(self, done, what, timeout=60.0):
        t = time.perf_counter()
        while not done():
            if time.perf_counter() - t > timeout:
                raise TimeoutError(f"{what} did not finish in {timeout} s")
            QApplication.processEvents()
            time.sleep(0.002)

    def walk(self, start=0, length=ROWS, ask=None):
        """Walks the window, by `ask` when the walk is another's to start, and waits for its chain."""
        self.walked.clear()
        self.series.clear()
        (ask or (lambda: self.worker.set_window(start, length, by=HAND)))()
        if not self.worker.isRunning():
            self.worker.start()
        self.wait(lambda: self.walked and self.walked[-1] == (length, length) and self.series, "the walk")

    def change(self, nid, **params):
        self.doc.node(nid).params.update(params)
        self.graph.sync()
        return self.worker.invalidate

    def bake(self):
        self.walk(0, 2)
        self.worker.bake("bake", "simulation")
        self.wait(lambda: self.baked, "the bake")
        if isinstance(self.baked[0], Exception):
            raise self.baked[0]
        return self.baked[0]

    def settle(self):
        """Waits until the buckets written so far are settled, a later one begun, so a class that judges buckets has judged them."""
        now = int(time.perf_counter() // self.ledger.width)
        self.wait(lambda: (v := self.ledger.view()).first + len(v.buckets) > now + 3, "the next buckets")

    def seen(self):
        view = self.ledger.view()
        self.log.read(view)
        return Seen(self.log, view, context(self.graph))

    def fresh(self):
        """A new graph, decoder and worker under the ledger it has, so the next walk is cold in one history."""
        self._shut()
        self._open(self.ledger)

    def _shut(self):
        self.lateness.stop()
        if self.worker.isRunning():
            self.worker.stop()
        self.graph.close()
        self.graph.decoder.close()

    def close(self):
        self.machine.close()
        self._shut()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _fault(**run):
    """Marks a simulation, a function of a _Run, with what its _Run is made with."""
    def mark(fault):
        fault.run = run
        return fault
    return mark


@_fault(served=True)
def unread(r):
    """A bake served on a fresh graph: the window walk folds gray and work, which nothing reads."""
    r.walk()


@_fault(memo_bytes=ROWS * ROW * 2)
def memo(r):
    """A memo that holds under half the window, walked twice."""
    r.walk()
    r.walk()


@_fault(cache_bytes=8 * ROW * 3)
def cache(r):
    """A plate cache that holds eight rows, and a change at gray, which decodes the window again."""
    r.walk()
    r.walk(ask=r.change("gray", k=1))


@_fault(served=True, pinned=("gray", "work"), cache_bytes=8 * ROW * 3)
def reader(r):
    """A served reader's cache that holds eight rows, and a change under it; what is upstream is
    pinned, so its folds are read."""
    r.walk()
    r.walk(ask=r.change("edge", k=1))


@_fault()
def grows(r):
    """pile, which does not step, costing by the rows it is run over."""
    r.tools["pile"].ms = 0.1
    r.walk()


@_fault()
def seeks(r):
    """work reading the row half a clip away beside its own."""
    r.tools["work"].far = ROWS // 2
    r.walk()


@_fault()
def slower(r):
    """Two halves of the clip under one plan, work five times as slow over the second."""
    r.tools["work"].ms = MS
    r.walk(0, ROWS // 2)
    r.tools["work"].ms = 5 * MS
    r.walk(ROWS // 2, ROWS // 2)


@_fault()
def held(r):
    """Two halves of the clip under one plan, the worker held between rows over the second, in no span."""
    r.walk(0, ROWS // 2)
    r.worker.walked.connect(lambda done, n: _spin(3 * MS), Qt.ConnectionType.DirectConnection)
    r.walk(ROWS // 2, ROWS // 2)


@_fault(pinned=("gray", "work", "bake", "edge"))
def slot(r):
    """A slot of the GUI thread's that spins at every row, holding the interpreter the worker then
    waits for. The wait lands in whatever span the worker is in, the folds among them, so the frame
    nodes are pinned and their folds, grown by it, are read."""
    r.worker.walked.connect(r.slot("walked", lambda done, n, *was: _spin(3 * MS)))
    r.walk()


@_fault(pinned=("gray", "work", "bake", "edge"))
def signals(r):
    """Rows a tenth as long, and a slot of the GUI thread's that does a little at every one. The
    frame nodes are pinned, so the folds of so short a row are read."""
    r.tools["work"].ms = r.tools["edge"].ms = MS / 10
    r.worker.walked.connect(r.slot("walked", lambda done, n, *was: _spin(MS / 20)))
    r.walk()


@_fault()
def frozen(r):
    """A slot of the GUI thread's that sleeps, the walk done: the GUI thread late under a turn, and no tool waiting beside it."""
    r.walk()
    r.settle()
    r.slot("walked", time.sleep)(HOLD)
    r.settle()


@_fault()
def holds(r):
    """work holding the interpreter through one call on one row: the GUI thread late under no turn of its own."""
    r.tools["work"].hold = HOLD
    r.walk()
    r.settle()


@_fault()
def unspanned(r):
    """The GUI thread kept from its loop under no span, and no walk at all."""
    r.settle()
    time.sleep(HOLD)
    r.settle()


def _again(r, by, times=40, every=4):
    """Asks for the window again at every `every` rows, `times` times, as `by`, then lets it walk.
    The ask is made on the worker's thread as the row lands, a queued one finding the walk rows on."""
    left = [times]

    def ask(done, n, *was):
        if left[0] and done == every:
            left[0] -= 1
            r.worker.set_window(0, ROWS, by=by)
    hook = r.worker.walked.connect(ask, Qt.ConnectionType.DirectConnection)
    r.walk()
    r.worker.walked.disconnect(hook)
    r.settle()


@_fault()
def again(r):
    """The window asked for again every few rows by no hand and no edit, forty times over."""
    _again(r, "asked")


def _healthy(*steps):
    @_fault()
    def run(r):
        for step in steps:
            step(r)
    return run


def _scrubbed(r):
    hook = r.worker.walked.connect(lambda done, n: done == 8 and r.worker.request_row(ROWS - 8))
    r.walk()
    r.worker.walked.disconnect(hook)


SIMULATIONS = {"unread": (unread, "unread"), "memo": (memo, "thrash"), "cache": (cache, "thrash"), "reader": (reader, "thrash"),
               "grows": (grows, "grows"), "seeks": (seeks, "seeks"), "slower": (slower, "slower"),
               "held": (held, "slower"), "slot": (slot, "waits"), "signals": (signals, "signals"),
               "frozen": (frozen, "late"), "holds": (holds, "late"), "unspanned": (unspanned, "late"),
               "again": (again, "restarts")}     # name -> (it, the class it builds)
SERVED = {"unread", "reader", "bake"}      # the simulations that write a bake
HEALTHY = {"walk": _healthy(_Run.walk), "rewalk": _healthy(_Run.walk, _Run.walk),
           "midclip": _healthy(lambda r: r.walk(ROWS // 4, ROWS // 2)), "scrub": _healthy(_scrubbed),
           "bake": _healthy(_Run.walk, _Run.bake), "drag": _healthy(lambda r: _again(r, HAND))}      # each a way of walking the graph that is no fault


def _named(name):
    return SIMULATIONS[name][0] if name in SIMULATIONS else HEALTHY[name]


def run(name, folder=None):
    """What simulation `name`, a key of SIMULATIONS or HEALTHY, leaves the log holding: a Seen. It
    writes under `folder`, a temporary one when none is given."""
    with tempfile.TemporaryDirectory() as tmp, _Run(str(folder or tmp), **_named(name).run) as r:
        _named(name)(r)
        return r.seen()


def show(name, rounds=None, folder=None):
    """Opens the monitor on simulation `name`'s run and repeats its fault, each time after the first
    on a fresh graph under the one ledger, `rounds` times or until the window is closed; returns the
    window, closed, holding what its last poll read."""
    with tempfile.TemporaryDirectory() as tmp, _Run(str(folder or tmp), **_named(name).run) as r:
        win, n = Window(r), 0
        win.show()
        while win.isVisible() and (rounds is None or n < rounds):
            if n:
                r.fresh()
            _named(name)(r)
            n += 1
        win.refresh()
        win.close()
        return win


if __name__ == "__main__":
    wrong = 0
    asked = [n for a in sys.argv[1:] if a != "--show" for n in ([s for s, (_, kind) in SIMULATIONS.items() if kind == a] or [a])]    # a class names its simulations
    if "--show" in sys.argv:
        QApplication.instance() or QApplication([])
        show((asked or ["walk"])[0])
        sys.exit(0)
    for name in asked or [*SIMULATIONS, *HEALTHY]:
        seen = run(name)
        found, want = {e.problem.kind for e in seen.log.ordered()}, {SIMULATIONS[name][1]} if name in SIMULATIONS else set()
        wrong += found != want
        print(f"{name}: {'as expected' if found == want else f'expected {sorted(want)}'}")
        print("\n".join("  " + line(e) for e in seen.log.ordered()) or "  nothing found")
    sys.exit(1 if wrong else 0)
