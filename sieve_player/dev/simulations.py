r"""The simulations: each builds one fault on purpose with the player's own Graph and Worker, on a clip
it writes under the folder it is handed, and returns what the catalogue's log then holds.
The graph is one, video, gray, work, edge, then mean and pile as the chain; a fault is one
departure from HEALTHY's ways of walking it. One that serves a file has cut between the video and
gray, a node whose tool answers a second clip as its cut file.
With --show the monitor is opened on the first one named and its fault repeated until it is closed;
with --long the clip is LONG rows, and each entry says how far into its walk it was first found.

    .venv\Scripts\python -m sieve_player.dev.simulations [name] [--show] [--long]
"""
import os
import sys
import tempfile
import threading
import time
from collections import namedtuple
from types import SimpleNamespace as Tool

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from .. import document as D
from ..catalogue import CLASSES, STALLS, WHOLE, Log
from ..decoder import Decoder
from ..graph import Graph
from ..ledger import SETTLES_BY, Ledger
from ..machine import Watch
from ..pace import Pace
from ..registry import by_name
from ..report import line
from ..stream import HAND, Emitter
from ..worker import Worker
from .timeview import Window, context

ROWS, H, W = 64, 48, 64
LONG = 2048         # the rows of a clip whose walk runs over buckets enough to be judged under way
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


def _clip(path, rows, shift=0):
    w = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), 30, (W, H))
    y, x = np.mgrid[:H, :W]
    for r in range(rows):
        f = ((x * 2 + y + 5 * r + shift) % 180).astype(np.uint8)
        w.write(cv2.merge((f, f // 2, 255 - f)))
    w.release()
    return path


def _tools(rows):
    """The graph's tools, made anew so a fault set on one is no other simulation's."""
    def frame(name, expects, fn):
        t = Tool(NAME=name, KIND="frame", EXPECTS=expects, PRODUCES="gray", PARAMS={"k": {"default": 0}}, ms=0.0, far=0, hold=0.0, block=None, grind=None)

        def run(frames, row, params):
            f = frames(row)
            if t.far:
                frames((row + t.far) % frames.count)
            _spin(t.ms)
            if t.hold and row == rows // 2:
                _hold(t.hold)
            if t.block is not None and row == rows // 2:
                t.block.wait()
            while t.grind is not None and row == rows - 1 and not t.grind.is_set():
                _hold(HOLD)
            return fn(f, params)
        t.run = run
        return t

    mean = Tool(NAME="mean", KIND="series", EXPECTS="gray", PRODUCES="signal",
                fold=lambda f: np.array([f.mean()], np.float64),
                run=lambda s, p: {"signal": np.asarray(s.data, np.float32).reshape(len(s.data))},
                step=lambda state, row, i, p: (None, {"signal": np.float32(row[0])}))
    pile = Tool(NAME="pile", KIND="series", EXPECTS="signal", PRODUCES="signal", ms=0.0, long=None)

    def whole(s, p):
        _spin(pile.ms * len(s.data))
        if pile.long is not None and len(s.data) >= pile.long[0]:
            (_, seconds), pile.long = pile.long, None
            time.sleep(seconds)
        return {"signal": np.asarray(s.data, np.float32)}
    pile.run = whole
    gray = frame("gray", "bgr", lambda f, p: f[..., 1] + np.uint8(p["k"]))
    work, edge = frame("work", "gray", lambda f, p: f), frame("edge", "gray", lambda f, p: f + np.uint8(p["k"]))
    work.ms = edge.ms = MS
    return by_name((gray, work, edge, mean, pile))


def _cut(path):
    """A node that passes its frame through, whose cut file is the clip at `path`."""
    return Tool(NAME="cut", KIND="frame", EXPECTS="bgr", PRODUCES="bgr", run=lambda frames, row, params: frames(row),
                cut_file=lambda video, footage, params: path)


class _Run:
    """One simulation's graph, its stream, worker, ledger and log under `folder`, closed on leaving, on a clip of `rows` rows. `limits` are
    the stores', `memo_bytes`, said for a clip of ROWS and scaled to `rows`, and `cache_bytes`, and `sample`, the seconds between the machine's samples."""

    def __init__(self, folder, served=False, pinned=(), rows=ROWS, **limits):
        QApplication.instance() or QApplication([])
        self.rows, self.tools = rows, _tools(rows)
        self.path = _clip(os.path.join(folder, "clip.avi"), rows)
        if served:      # another clip than the video's, so the two are keyed apart
            self.tools = {"cut": _cut(_clip(os.path.join(folder, "cut.avi"), rows, shift=7)), **self.tools}
        self.doc = D.from_tools(list(self.tools.values()), self.path)
        self.doc.pinned = list(pinned)
        self.limits = {k: v * rows // ROWS if k == "memo_bytes" else v for k, v in limits.items()}
        self.worker, self.graph, self.dump = None, None, None
        self._open(Ledger(timed=lambda: self.stream.turn("monitor", "ledger"), watch=Log()))
        self.machine = Watch(lambda *sample: self.ledger.sample(*sample), limits.get("sample", 1.0),
                             still_out=lambda cpu: self.stream.still_out(cpu))     # one for the run: its counters take 0.4 s to open

    def _open(self, ledger):
        cache = self.limits.get("cache_bytes")
        self.stream = Emitter()
        self.graph = Graph(self.doc, Decoder(self.path, **({} if cache is None else {"cache_bytes": cache})), self.tools,
                           stream=self.stream, **{k: v for k, v in self.limits.items() if k == "memo_bytes"})
        self.ledger, self.pace = ledger, Pace()
        self.stream.on_event = ledger.event
        self.graph.sync()       # the plan, into the ledger
        self.graph.watch(self.doc.pinned)
        self.worker = Worker(self.graph, every=EVERY)
        self.walked, self.series = [], []
        self.worker.walked.connect(self.slot("walked", lambda done, n, *was: (self.walked.append((done, n)),
                                                                             self.pace.row("window", done, n, *was))))
        self.worker.seriesReady.connect(self.slot("seriesReady", lambda *a: self.series.append(a)))
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

    def walk(self, start=0, length=None, ask=None):
        """Walks the window, the whole clip with no `length`, by `ask` when the walk is another's to start, and waits for its chain."""
        length = self.rows if length is None else length
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

    def settle(self):
        """Waits until the buckets written so far are settled, so the log has been told of them and of the walks over them."""
        now = int(time.perf_counter() // self.ledger.width)
        self.wait(lambda: (self.ledger.view().settled or 0) >= now, "the buckets to settle")

    def seen(self):
        self.settle()
        view = self.ledger.view()
        return Seen(view.found, view, context(self.graph))

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


@_fault()
def unread(r):
    """edge reading gray, so nothing reads work, and the graph told the plot shows work where the
    stream is told of nothing: the window walk runs work for its fold, which nothing reads."""
    r.doc.connect("gray", "edge")
    r.graph.sync()
    r.graph.watch(["work"])
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


@_fault(served=True, cache_bytes=8 * ROW * 3)
def reader(r):
    """A served file's cache that holds eight rows, and a change at gray, which decodes the window again."""
    r.walk()
    r.walk(ask=r.change("gray", k=1))


@_fault()
def grows(r):
    """pile, which does not step, costing by the rows it is run over."""
    r.tools["pile"].ms = 0.1 * ROWS / r.rows     # the same share of the walk whatever its range
    r.walk()


@_fault()
def seeks(r):
    """work reading the row half a clip away beside its own."""
    r.tools["work"].far = r.rows // 2
    r.walk()


@_fault()
def slower(r):
    """Two halves of the clip under one plan, work five times as slow over the second."""
    r.tools["work"].ms = MS
    r.walk(0, r.rows // 2)
    r.tools["work"].ms = 5 * MS
    r.walk(r.rows // 2, r.rows // 2)


@_fault()
def held(r):
    """Two halves of the clip under one plan, the worker held between rows over the second, in no span."""
    r.walk(0, r.rows // 2)
    r.worker.walked.connect(lambda done, n: _spin(3 * MS), Qt.ConnectionType.DirectConnection)
    r.walk(r.rows // 2, r.rows // 2)


@_fault(pinned=("gray", "work", "edge"))
def slot(r):
    """A slot of the GUI thread's that spins at every row, holding the interpreter the worker then
    waits for. The wait lands in whatever span the worker is in, the folds among them, so the frame
    nodes are pinned and their folds, grown by it, are read."""
    r.worker.walked.connect(r.slot("walked", lambda done, n, *was: _spin(3 * MS)))
    r.walk()


@_fault(pinned=("gray", "work", "edge"))
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


@_fault()
def stuck(r):
    """work not returning from one call, the window walk half done: what the log holds while the call is still out."""
    out = r.tools["work"].block = threading.Event()
    try:
        r.worker.set_window(0, r.rows, by=HAND)
        r.worker.start()
        r.wait(lambda: any(kind == "stalls" for kind, _, _ in r.ledger.view().found.entries), "the walk to be found finishing no row", STALLS + 10)
        view = r.ledger.view()
        return Seen(view.found, view, context(r.graph))
    finally:
        out.set()
        r.wait(lambda: r.walked and r.walked[-1] == (r.rows, r.rows) and r.series, "the walk")


@_fault()
def unreturned(r):
    """work holding the interpreter call after call in a scrub's row it does not return from, no walk open:
    what the log holds of the GUI thread's lateness while the call is still out."""
    out, ready = threading.Event(), []
    r.tools["work"].grind = out
    hook = r.worker.rowReady.connect(ready.append)
    r.walk(0, r.rows // 2)
    r.settle()
    try:
        r.worker.request_row(r.rows - 1)
        r.wait(lambda: any(kind == "late" for kind, _, _ in r.ledger.view().found.entries), "the GUI thread to be found late", SETTLES_BY + 10)
        view = r.ledger.view()
        assert "worker" in view.still_out, "the call returned before the log was read"
        return Seen(view.found, view, context(r.graph))
    finally:
        out.set()
        r.wait(lambda: ready, "the scrub's row")
        r.worker.rowReady.disconnect(hook)


def _again(r, by, times=40, every=4):
    """Asks for the window again at every `every` rows, `times` times, as `by`, then lets it walk.
    The ask is made on the worker's thread as the row lands, a queued one finding the walk rows on."""
    left = [times]

    def ask(done, n, *was):
        if left[0] and done == every:
            left[0] -= 1
            r.worker.set_window(0, r.rows, by=by)
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
    hook = r.worker.walked.connect(lambda done, n: done == 8 and r.worker.request_row(r.rows - 8))
    r.walk()
    r.worker.walked.disconnect(hook)


def _clip_walk(r, at, then):
    """Walks the window, then the clip, calling `then` once as the clip's row `at` is told, and waits for the clip walk to close."""
    told = []
    r.walk()
    hook = r.worker.clipWalked.connect(lambda done, n, *was: (told.append((done, n)), done == at and then()))
    r.worker.walk_clip(HAND)
    r.wait(lambda: told and told[-1][0] == told[-1][1], "the clip walk")
    r.worker.clipWalked.disconnect(hook)


def _whole_long(r):
    """pile, run whole, taking longer than a lane may finish no row over one run short of the window's end."""
    r.tools["pile"].long = r.rows // 2, STALLS + 1.5
    r.walk()


def _given_long(r):
    """A clip walk given every stepped node, begun at its last row: pile's one run over the clip taking longer than that."""
    made, g = [], r.graph
    hook = r.worker.clipReady.connect(lambda results, start, fps: made.append(results))
    r.walk()        # the window is the clip, so what its chain made is what a clip walk would step
    r.tools["pile"].long = r.rows, STALLS + 1.5
    r.worker.give_clip(r.rows, {nid: (g.entry(nid).raw_key, {f: v for f, v in r.series[-1][0][nid].items() if f not in ("gate", "key")})
                                for nid in g.chain if g.entry(nid).steps or nid in g.heads})
    r.worker.walk_clip(HAND)
    r.wait(lambda: made, "the clip walk given its stepped nodes")
    r.worker.clipReady.disconnect(hook)
    assert r.tools["pile"].long is None, "the clip walk did not run pile over the clip"


def _behind(r):
    """The window asked for again with the clip walk under way, which waits behind it."""
    r.walked.clear()
    _clip_walk(r, 8, lambda: r.worker.set_window(r.rows // 4, r.rows // 2, by=HAND))
    r.wait(lambda: r.walked and r.walked[-1] == (r.rows // 2, r.rows // 2), "the window walked again")


SIMULATIONS = {"unread": (unread, "unread"), "memo": (memo, "thrash"), "cache": (cache, "thrash"), "reader": (reader, "thrash"),
               "grows": (grows, "grows"), "seeks": (seeks, "seeks"), "slower": (slower, "slower"),
               "held": (held, "slower"), "slot": (slot, "waits"), "signals": (signals, "signals"),
               "frozen": (frozen, "late"), "holds": (holds, "late"), "unspanned": (unspanned, "late"),
               "again": (again, "restarts"), "stuck": (stuck, "stalls"), "unreturned": (unreturned, "late")}     # name -> (it, the class it builds)
HEALTHY = {"walk": _healthy(_Run.walk), "rewalk": _healthy(_Run.walk, _Run.walk),
           "midclip": _healthy(lambda r: r.walk(r.rows // 4, r.rows // 2)), "scrub": _healthy(_scrubbed),
           "drag": _healthy(lambda r: _again(r, HAND)),
           "behind": _healthy(_behind), "stopped": _healthy(lambda r: _clip_walk(r, r.rows // 2, r.worker.stop_clip)),
           "wholelong": _healthy(_whole_long), "givenlong": _healthy(_given_long)}      # each a way of walking the graph that is no fault


def under_way(entry, view):
    """How far the walk `entry` was first found in had got, as written, where it was short of its
    last row then: a sighting's time is its walk's last progress as it was judged. "" otherwise."""
    for w in view.walks:
        if w.t0 < entry.first < w.t1:
            return f"; first found {entry.first - w.t0:.2f} s into a {w.lane} walk of {w.t1 - w.t0:.2f} s"
    return ""


def _named(name):
    return SIMULATIONS[name][0] if name in SIMULATIONS else HEALTHY[name]


def run(name, folder=None, rows=ROWS):
    """What simulation `name`, a key of SIMULATIONS or HEALTHY, leaves the log holding, or what it
    read part way where it returns that: a Seen. It writes under `folder`, a temporary one when
    none is given, a clip of `rows` rows: LONG of them is a walk over buckets enough to be judged
    before its last row."""
    with tempfile.TemporaryDirectory() as tmp, _Run(str(folder or tmp), rows=rows, **_named(name).run) as r:
        return _named(name)(r) or r.seen()


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
    rows = LONG if "--long" in sys.argv else ROWS
    asked = [n for a in sys.argv[1:] if not a.startswith("--") for n in ([s for s, (_, kind) in SIMULATIONS.items() if kind == a] or [a])]    # a class names its simulations
    if "--show" in sys.argv:
        QApplication.instance() or QApplication([])
        show((asked or ["walk"])[0])
        sys.exit(0)
    for name in asked or [*SIMULATIONS, *HEALTHY]:
        t = time.perf_counter()
        seen = run(name, rows=rows)
        took = time.perf_counter() - t
        found, want = {e.problem.kind for e in seen.log.ordered()}, {SIMULATIONS[name][1]} if name in SIMULATIONS else set()
        late = [e.problem.subject for e in seen.log.ordered()       # with --long, a class judged under way is to be found there
                if rows == LONG and e.problem.kind in want and e.problem.kind in CLASSES and e.problem.kind not in WHOLE and not under_way(e, seen.view)]
        wrong += found != want or bool(late)
        print(f"{name}: {'as expected' if found == want else f'expected {sorted(want)}'}{f', {late} not found under way' if late else ''}, in {took:.1f} s")
        print("\n".join(f"  {line(e)}{under_way(e, seen.view)}" for e in seen.log.ordered()) or "  nothing found")
    sys.exit(1 if wrong else 0)
