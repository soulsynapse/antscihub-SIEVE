"""The one thread that runs tools: the ladder, a scrub, then the window walk, then the clip walk, and the
condition it waits on. Each rung is a job, _Scrub and two of walk.py's _Walk, holding its own state and doing one
thing with a turn; the GUI side sets a job's ask under the lock and the scheduler takes it and tells the job to
begin, once. The clip walk runs behind a finished window so what is viewed never waits on it, and a frame change
abandons it and its rows."""
import sys
import threading
import traceback

from PySide6.QtCore import QThread, Signal

from .decoder import EndOfStream
from .graph import Cancelled
from .stream import ASKED, EDIT
from .walk import _Walk

STOP_PATIENCE_MS = 10_000  # how long stop() waits before saying on stderr what it is waiting for


class _Scrub:
    name = "scrub"      # the lane its events are in

    def __init__(self, graph, rowReady, failed):
        self.graph, self.rowReady, self.failed = graph, rowReady, failed
        self.row = None
        self.plan = None    # the Plan a turn runs under, set by whoever drives the job before it

    def turn(self, row):
        self.row = row
        g, p = self.graph, self.plan
        with g.scrubbing():       # the display's jump lands on its own cursor, not the walk's
            g.compute(p.shown, row, p=p)
            if p.over is not None:
                g.compute(p.over, row, p=p)
            for nid in g.drawing(p):
                g.compute(nid, row, p=p)
        self.rowReady.emit(row)

    def cancelled(self):
        pass

    def ended(self):
        pass            # the display asked past the end; the window follows the count and asks again

    def raised(self, exc):
        self.failed.emit(self.row, getattr(exc, "sieve_node", ""))


class Worker(QThread):
    rowReady = Signal(int)                    # a requested row is computed and peekable
    walked = Signal(int, int, int)            # rows done, rows in window, and of those done the rows that ran; the rest a store held
    seriesReady = Signal(object, int, float)  # {node: result} for the series chain, each gated and keyed, start, fps
    densityReady = Signal(object, int)        # {node: (rows, BINS) counts} per plane the walk computes, start
    failed = Signal(int, str)                 # a tool raised at this row, on this node; a walk closes at the rows it has, as a refused one does, a display request is dropped
    clipWalked = Signal(int, int, int)        # as walked, over the clip; done == total when the clip walk is not running
    clipReady = Signal(object, int, float)    # as seriesReady, over the clip walk's rows; {} when the walk was abandoned
    clipRefused = Signal(str)                 # the clip walk did not start, or stopped short of the clip, and why
    walkRefused = Signal(str)                 # the window walk closed short of the window, and why: its stack passed STACK_BYTES
    shortened = Signal(int)                   # the stream ended short of the container's claim: the count as the decoder now has it

    def __init__(self, graph, every=30, tell_every=0.0):
        """`every` is the cadence, in rows walked, at which either range runs its chain;
        `tell_every`, the seconds between a range's `walked` or `clipWalked`, its end always told,
        and 0 tells of every row; a range's chain result and densities go out no oftener, its end's always."""
        super().__init__()
        self.graph, self.every = graph, every
        self._cv = threading.Condition()
        self._want = None
        self._stop = False
        self._series_dirty = False
        self._clip_on = False                 # whether a clip walk is wanted
        self._scrub = _Scrub(graph, self.rowReady, self.failed)
        self._win = _Walk(graph, name="window", every=every, progress=self.walked, ready=self.seriesReady,
                          refused=self.walkRefused, failed=self.failed, densities=self.densityReady, tell_every=tell_every)
        self._clip = _Walk(graph, name="clip", every=every, progress=self.clipWalked, ready=self.clipReady,
                           refused=self.clipRefused, failed=self.failed, tell_every=tell_every)

    # -- GUI-side calls --------------------------------------------------
    def request_row(self, row):
        with self._cv:
            self._want = row
            self._cv.notify()

    def set_window(self, start, length, spared=False, given=None, by=ASKED):
        """Walk the window from `start`. `spared`, the caller holds the chain's results over it and
        the chain is not run; `given`, node to (raw key, fields over the window, the code they were made under or None), it holds those
        stepped nodes' and the walk steps the rest from them. The densities of what the plot shows,
        by watch(), are folded either way. `by`, one of stream.BEGUN_BY, is what the walk's begin
        says began it: the caller says where a hand or an edit did."""
        with self._cv:
            self._win.ask, self._win.asked, self._win.by = (start, length, spared, dict(given or {})), True, by
            self._cv.notify()

    def watch(self, nodes):
        """`nodes` are what the plot shows, as Graph.watch takes them: the window folds the
        densities of those and no other, one it had not folded from the window's first row, with
        the rows the chain has standing."""
        self.graph.watch(nodes)
        with self._cv:
            self._cv.notify()

    def invalidate(self):
        """A frame tool changed: restart the walk from the window start, and drop the clip walk,
        whose rows were of a graph that is gone."""
        with self._cv:
            self._win.asked = self._clip.asked = True
            self._win.by = self._clip.by = EDIT
            self._win.ask = (*self._win.ask[:2], False, {})    # what was held was of the graph that is gone
            self._clip_on = False
            self._cv.notify()

    def rerun_series(self):
        """Only the series tool changed: rerun it on the stack we already have, and on the clip's."""
        with self._cv:
            self._series_dirty = True
            self._cv.notify()

    def give_clip(self, rows, given):
        """What the caller holds of the chain's stepped nodes over a clip of `rows` rows, as
        set_window's `given`: the next clip walk steps the rest from it, and one given every
        stepped node and every head has no row to walk and ends in a turn."""
        with self._cv:
            self._clip.ask = (0, rows, False, dict(given))

    def walk_clip(self, by=ASKED):
        """Walk the whole clip, from its first row, once the window is walked; `by` as set_window's."""
        with self._cv:
            self._clip.asked, self._clip.by = True, by
            self._clip_on = True
            self._cv.notify()

    def stop_clip(self):
        """Halt the clip walk where it is; the rows it has stand, and the chain's result over them goes out."""
        with self._cv:
            self._clip_on = False
            self._cv.notify()

    def stop(self):
        """Halts the graph, so a run of many reads dies at its next one, then joins the thread."""
        self.graph.halt = True
        with self._cv:
            self._stop = True
            self._cv.notify()
        if not self.wait(STOP_PATIENCE_MS):
            print(f"worker still running {STOP_PATIENCE_MS // 1000} s after stop: a tool in a loop no read interrupts", file=sys.stderr)
            self.wait()

    # -- thread side -----------------------------------------------------
    def run(self):
        threading.current_thread().name = "worker"      # what the probe's events name as their thread
        try:
            self._serve()
        except BaseException:
            traceback.print_exc()   # _serve answers for a tool's exceptions; one reaching here ends the thread, and `finished` says so
            raise

    def _serve(self):
        """The loop: waits until a rung is due, takes its turn, and reads the asks again."""
        self.graph.stream.rest(False)       # a turn due as the thread starts is taken with no wait: the stream is told from the first that this thread says when it rests
        while True:
            with self._cv:
                turn = None if self._stop else self._turn()
            if turn is None:
                self.graph.stream.rest(True)        # outside the lock: a reader of the stream may fold on this thread
                with self._cv:
                    while not self._stop and (turn := self._turn()) is None:
                        self._cv.wait()
                    if self._stop:
                        return
                self.graph.stream.rest(False)
            serves, steps = turn
            self.graph.readers.reap()
            job = None
            try:
                for job, act in steps:
                    self.graph.serving(serves, job.name)
                    act()
            except Cancelled:
                job.cancelled()     # the graph moved on under the row, or we are stopping: the loop reads the new state
            except EndOfStream:
                self.shortened.emit(self.graph.count)
                job.ended()
            except Exception as e:
                traceback.print_exc()
                job.raised(e)

    def _turn(self):
        """The ladder: a scrub, then the window walk, then a refold of the window, then the clip walk. Returns the first rung due as what
        its events serve and the (job, call) steps that are its turn, or None when no rung
        is, which is the condition the loop waits on, so waking means turning. Called under the
        lock; the ask of the rung picked is taken here, so one landing meanwhile is not lost. The
        graph's Plan is taken here, once, and is the one every job's turn and its handlers read."""
        scrub, win, clip, g = self._scrub, self._win, self._clip, self.graph
        p = scrub.plan = win.plan = clip.plan = g.snapshot()
        if self._want is not None:
            row, self._want = self._want, None
            return "scrub", [(scrub, lambda: scrub.turn(row))]
        count = g.count
        fed = (e := p.entries.get(p.walk)) is not None and e.fed
        if win.asked:
            (start, length, spared, given), by, win.asked = win.ask, win.by, False
            s = max(0, min(start, count - 1))
            n = max(0, min(length, count - s)) if fed else 0   # nothing reaches a walked node: nothing to walk until the next change

            def begin():
                win.spared, win.given = spared, given if n == length else {}  # given is over the rows asked: a clamped range takes none
                win.begin(s, n, by)
            return "walk", [(win, begin)]
        if self._series_dirty:
            self._series_dirty = False
            if fed and win.i:
                return "walk", [(win, win.emit)] + ([(clip, clip.emit)] if clip.i else [])
        if fed and win.i < win.length:
            return "walk", [(win, win.turn)]
        if fed and (win.refolding or win.behind()):
            return "walk", [(win, win.refold)]
        if clip.asked:
            on, by, clip.asked = self._clip_on, clip.by, False

            _, rows, _, given = clip.ask

            def begin():
                clip.given = given if rows == count else {}
                clip.begin(0, count if on and fed else 0, by)
                if clip.length and clip.given and not clip.stale_given() and all(
                        nid in clip.given for nid in p.chain if p.entries[nid].steps or nid in p.heads):
                    clip.i = clip.length - 1    # nothing is left to step and no head reads a row: the last turn runs what runs whole and ends the walk
                if not clip.length:
                    clip.ready.emit({}, 0, g.fps)
                clip.report()
            return "walk", [(clip, begin)]
        if clip.i < clip.length:
            if self._clip_on and fed:
                return "walk", [(clip, clip.turn)]
            return "walk", [(clip, clip.halt), (clip, clip.emit)]   # the chain over the rows it stopped at: the cadence's last result is short of them
        return None
