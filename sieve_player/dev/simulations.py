r"""The simulations: each builds one fault on purpose with the player's own Graph and Worker, on a clip
and a store it writes under the folder it is handed, and returns what the catalogue's log then holds.
The graph is one, video, gray, work, bake, edge, then mean and pile as the chain; a fault is one
departure from HEALTHY's ways of walking it. Those that serve a bake need ffmpeg, as a bake does.

    .venv\Scripts\python -m sieve_player.dev.simulations [name]
"""
import os
import sys
import tempfile
import time
from collections import namedtuple
from types import SimpleNamespace as Tool

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from tools import bake

from .. import document as D
from ..catalogue import Log, line
from ..decoder import Decoder
from ..graph import Graph
from ..ledger import Ledger
from ..store import Store, commit
from ..worker import Worker

ROWS, H, W = 64, 48, 64
EVERY = 4           # the chain's cadence, so a node run whole runs in every part of the range
MS = 1.0            # what work and edge each spin a row, well over the clip's decode and the folds
ROW = H * W

Seen = namedtuple("Seen", "log view context")


def _spin(ms):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        pass


def context(graph, dump=None):
    """What an entry's text takes beside the view, read off `graph`; `dump` is the path of the
    dump being written, when one is."""
    d = graph.decoder
    return {"document": graph.doc.to_dict(), "video": d.path, "memo_limit": graph.memo.limit, "commit": commit(), "dump": dump,
            "decoder": {k: getattr(d, k, None) for k in ("width", "height", "fps", "count", "output", "cache_limit")}}


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
        t = Tool(NAME=name, KIND="frame", EXPECTS=expects, PRODUCES="gray", DEFAULTS={"k": 0}, ms=0.0, far=0)

        def run(frames, row, params):
            f = frames(row)
            if t.far:
                frames((row + t.far) % frames.count)
            _spin(t.ms)
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
    """One simulation's graph, worker, ledger and log under `folder`, closed on leaving."""

    def __init__(self, folder, served=False, pinned=(), **limits):
        QApplication.instance() or QApplication([])
        self.tools, self.store = _tools(), Store(os.path.join(folder, "store"))
        self.path = _clip(os.path.join(folder, "clip.avi"))
        self.doc = D.from_tools(list(self.tools.values()), self.path)
        self.doc.pinned = list(pinned)
        self.limits, self.worker, self.graph = limits, None, None
        self._open(Ledger())
        if served:      # baked on one graph and served on a fresh one, so no store holds what is upstream of it
            D.land(self.doc.node("bake"), self.bake())
            self.close()
            self._open(Ledger())

    def _open(self, ledger):
        cache = self.limits.get("cache_bytes")
        self.graph = Graph(self.doc, Decoder(self.path, **({} if cache is None else {"cache_bytes": cache})), self.tools,
                           open_bake=self.store.open_bake, **{k: v for k, v in self.limits.items() if k == "memo_bytes"})
        self.ledger, self.log = ledger, Log()
        self.graph.on_event = ledger.event
        self.graph.sync()       # the plan, into the ledger
        self.worker = Worker(self.graph, every=EVERY, store=self.store)
        self.walked, self.series, self.baked = [], [], []
        self.worker.walked.connect(lambda done, n: self.walked.append((done, n)))
        self.worker.seriesReady.connect(lambda *a: self.series.append(a))
        self.worker.bakeDone.connect(lambda nid, b: self.baked.append(b))
        self.worker.bakeRefused.connect(lambda nid, why: self.baked.append(RuntimeError(why)))

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
        (ask or (lambda: self.worker.set_window(start, length)))()
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

    def seen(self):
        view = self.ledger.view()
        self.log.read(view)
        return Seen(self.log, view, context(self.graph))

    def close(self):
        if self.worker.isRunning():
            self.worker.stop()
        self.graph.close()
        self.graph.decoder.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def unread(folder):
    """A bake served on a fresh graph: the window walk folds gray and work, which nothing reads."""
    with _Run(folder, served=True) as r:
        r.walk()
        return r.seen()


def memo(folder):
    """A memo that holds under half the window, walked twice."""
    with _Run(folder, memo_bytes=ROWS * ROW * 2) as r:
        r.walk()
        r.walk()
        return r.seen()


def cache(folder):
    """A plate cache that holds eight rows, and a change at gray, which decodes the window again."""
    with _Run(folder, cache_bytes=8 * ROW * 3) as r:
        r.walk()
        r.walk(ask=r.change("gray", k=1))
        return r.seen()


def reader(folder):
    """A served reader's cache that holds eight rows, and a change under it; what is upstream is
    pinned, so its folds are read."""
    with _Run(folder, served=True, pinned=("gray", "work"), cache_bytes=8 * ROW * 3) as r:
        r.walk()
        r.walk(ask=r.change("edge", k=1))
        return r.seen()


def grows(folder):
    """pile, which does not step, costing by the rows it is run over."""
    with _Run(folder) as r:
        r.tools["pile"].ms = 0.1
        r.walk()
        return r.seen()


def seeks(folder):
    """work reading the row half a clip away beside its own."""
    with _Run(folder) as r:
        r.tools["work"].far = ROWS // 2
        r.walk()
        return r.seen()


def slower(folder):
    """Two halves of the clip under one plan, work three times as slow over the second."""
    with _Run(folder) as r:
        r.walk(0, ROWS // 2)
        r.tools["work"].ms *= 3
        r.walk(ROWS // 2, ROWS // 2)
        return r.seen()


def held(folder):
    """Two halves of the clip under one plan, the worker held between rows over the second, in no span."""
    with _Run(folder) as r:
        r.walk(0, ROWS // 2)
        r.worker.walked.connect(lambda done, n: _spin(3 * MS), Qt.ConnectionType.DirectConnection)
        r.walk(ROWS // 2, ROWS // 2)
        return r.seen()


def _healthy(*steps):
    def run(folder):
        with _Run(folder) as r:
            for step in steps:
                step(r)
            return r.seen()
    return run


def _scrubbed(r):
    hook = r.worker.walked.connect(lambda done, n: done == 8 and r.worker.request_row(ROWS - 8))
    r.walk()
    r.worker.walked.disconnect(hook)


SIMULATIONS = {"unread": (unread, "unread"), "memo": (memo, "thrash"), "cache": (cache, "thrash"), "reader": (reader, "thrash"),
               "grows": (grows, "grows"), "seeks": (seeks, "seeks"), "slower": (slower, "slower"),
               "held": (held, "slower")}     # name -> (it, the class it builds)
SERVED = {"unread", "reader", "bake"}      # the simulations that write a bake
HEALTHY = {"walk": _healthy(_Run.walk), "rewalk": _healthy(_Run.walk, _Run.walk),
           "midclip": _healthy(lambda r: r.walk(ROWS // 4, ROWS // 2)), "scrub": _healthy(_scrubbed),
           "bake": _healthy(_Run.walk, _Run.bake)}      # each a way of walking the graph that is no fault


def run(name, folder=None):
    """What simulation `name`, a key of SIMULATIONS or HEALTHY, leaves the log holding: a Seen. It
    writes under `folder`, a temporary one when none is given."""
    sim = SIMULATIONS[name][0] if name in SIMULATIONS else HEALTHY[name]
    if folder is not None:
        return sim(str(folder))
    with tempfile.TemporaryDirectory() as tmp:
        return sim(tmp)


if __name__ == "__main__":
    wrong = 0
    asked = [n for a in sys.argv[1:] for n in ([s for s, (_, kind) in SIMULATIONS.items() if kind == a] or [a])]    # a class names its simulations
    for name in asked or [*SIMULATIONS, *HEALTHY]:
        seen = run(name)
        found, want = {e.problem.kind for e in seen.log.ordered()}, {SIMULATIONS[name][1]} if name in SIMULATIONS else set()
        wrong += found != want
        print(f"{name}: {'as expected' if found == want else f'expected {sorted(want)}'}")
        print("\n".join("  " + line(e) for e in seen.log.ordered()) or "  nothing found")
    sys.exit(1 if wrong else 0)
