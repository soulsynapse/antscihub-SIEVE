"""The one thread that runs tools: the ladder, a scrub, then the window walk, then the clip walk, and the
condition it waits on. Each rung is a job, _Scrub or one of walk.py's _Walk, holding its own state and doing one
thing with a turn; the GUI side sets a job's ask under the lock and the scheduler takes it and tells the job to
begin, once. The clip walk runs behind a finished window so what is viewed never waits on it, and a frame change
abandons it and its rows. Behind the clip's own range the clip lane walks each cut in time of the plan's `timed`
alone, a third _Walk, from the cut's first row to its last, save one give_periods says is held, and over the
walked node's rows it says are. Behind its own range the window walks each cut in time it overlaps alone, a
fourth _Walk, over walk.window_legs, save one give_periods says is held whole."""
import sys
import threading
import traceback

from PySide6.QtCore import QThread, Signal

from .decoder import EndOfStream
from .graph import Cancelled
from .stream import ASKED, EDIT
from .walk import _Walk, period_keys, window_legs

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


def _walking(p, nid, cut):
    """The plan `p` with the timed Walk for its chain whose walked node is `nid` and which has `cut`
    among its cuts; None where `p` has none, or that node is not fed."""
    w = next((w for w in p.timed if p.entries[w.heads[0]].src == nid and cut in w.cuts), None)
    return None if w is None or not p.entries[nid].fed else p.of(w)


class _Left:
    """A walk's progress told with the count of `legs` left behind it."""

    def __init__(self, signal, legs):
        self.signal, self.legs = signal, legs

    def emit(self, done, total, ran):
        self.signal.emit(done, total, len(self.legs))


class _OfCut:
    """A walk of one cut in time's results told with what `walk` is walking: (its walked node, the cut)."""

    def __init__(self, signal):
        self.signal, self.walk = signal, None

    def emit(self, results, start, fps):
        self.signal.emit(results, start, (self.walk.walked, self.walk.cut), fps)


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
    periodWalked = Signal(int, int, int)      # rows done and rows in the cut in time the clip lane walks, and the cuts left behind it
    periodReady = Signal(object, int, float)  # as clipReady, over one cut in time walked whole from its first row, which is `start`
    windowPeriodWalked = Signal(int, int, int)            # as periodWalked, of the cuts in time the window walks
    windowPeriodReady = Signal(object, int, object, float)  # as seriesReady, over one cut in time the window walks, then (the node its walk reads, the cut.Record)

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
        self._legs = []                       # [(walked node, cut.Record)]: the cuts in time the clip lane is yet to walk, set as the clip walk begins
        self._period = _Walk(graph, name="clip", every=1 << 62, progress=_Left(self.periodWalked, self._legs), ready=self.periodReady,
                             refused=self.clipRefused, failed=self.failed, tell_every=tell_every)
        self._period.walked, self._legs_by = None, ASKED     # the walked node of the cut under way; what began the clip walk the legs are of
        self._period.keeps = True
        self._held_periods = {}               # (walked node, (first, end)) -> what give_periods was told of that cut
        self._window_legs = []                # walk.window_legs of the window as last asked, less the cuts held: the window is yet to walk them
        told = _OfCut(self.windowPeriodReady)
        self._window_period = told.walk = _Walk(graph, name="window", every=every, progress=_Left(self.windowPeriodWalked, self._window_legs),
                                                ready=told, refused=self.walkRefused, failed=self.failed, tell_every=tell_every)
        self._window_period.walked = None

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

    def give_periods(self, held):
        """What the caller holds of each cut in time, (the node its timed Walk's first head reads,
        (first, end) clamped to the count) to (keys, spared, given, handed): `keys` as period_keys says them of the plan it was
        read under, `spared` that every chain node's result over the cut is held, so the clip lane
        walks it not at all, `given` as give_clip's, and `handed` as _Walk's. One whose keys the
        plan has left is walked as though nothing were held."""
        with self._cv:
            self._held_periods = dict(held)

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
        """The ladder: a scrub, then the window walk, then a refold of the window, then each cut in time the window overlaps, then the clip walk, then each cut in time. Returns the first rung due as what
        its events serve and the (job, call) steps that are its turn, or None when no rung
        is, which is the condition the loop waits on, so waking means turning. Called under the
        lock; the ask of the rung picked is taken here, so one landing meanwhile is not lost. The
        graph's Plan is taken here, once, and is the one every job's turn and its handlers read."""
        scrub, win, clip, wp, g = self._scrub, self._win, self._clip, self._window_period, self.graph
        p = scrub.plan = win.plan = clip.plan = g.snapshot()
        if self._want is not None:
            row, self._want = self._want, None
            return "scrub", [(scrub, lambda: scrub.turn(row))]
        count = g.count
        fed = (e := p.entries.get(p.walk)) is not None and e.fed
        chained = fed and bool(p.chain)     # the clip's own range runs a chain or is not walked: the shown node alone is the window's to fold
        if win.asked:
            (start, length, spared, given), by, win.asked = win.ask, win.by, False
            s = max(0, min(start, count - 1))
            n = max(0, min(length, count - s)) if fed else 0   # nothing reaches a walked node: nothing to walk until the next change

            def begin():
                win.spared, win.given = spared, given if n == length else {}  # given is over the rows asked: a clamped range takes none
                win.begin(s, n, by)
                if wp.i < wp.length:
                    wp.halt()
                self._window_legs[:] = [(nid, c, a, b) for nid, c, a, b, _ in window_legs(p, s, max(0, min(length, count - s)), count)
                                        if not self._spared(p, nid, c, count)]
                wp.by = by
            return "walk", [(win, begin)]
        if self._series_dirty:
            self._series_dirty = False
            if fed and win.i:
                return "walk", [(win, win.emit)] + ([(clip, clip.emit)] if clip.i else [])
        if fed and win.i < win.length:
            return "walk", [(win, win.turn)]
        if fed and (win.refolding or win.behind()):
            return "walk", [(win, win.refold)]
        if wp.i < wp.length:
            if (sub := _walking(p, wp.walked, wp.cut)) is not None:
                wp.plan = sub
                return "walk", [(wp, wp.turn)]
            self._window_legs.clear()
            return "walk", [(wp, wp.halt)]
        while self._window_legs:
            nid, cut, a, b = self._window_legs.pop(0)
            if (sub := _walking(p, nid, cut)) is None:
                continue

            def begin(sub=sub, nid=nid, cut=cut, a=a, b=b):
                wp.plan, wp.walked, wp.cut, wp.spared, wp.given, wp.handed = sub, nid, cut, False, {}, None
                wp.begin(a, b - a, wp.by)
            return "walk", [(wp, begin)]
        if clip.asked:
            on, by, clip.asked = self._clip_on, clip.by, False

            _, rows, _, given = clip.ask

            def begin():
                clip.given = given if rows == count else {}
                clip.begin(0, count if on and chained else 0, by)
                self._legs[:] = [(p.entries[w.heads[0]].src, c) for w in p.timed for c in w.cuts] if on else []
                self._legs_by = by
                if clip.length and clip.given and not clip.stale_given() and all(
                        nid in clip.given for nid in p.chain if p.entries[nid].steps or nid in p.heads):
                    clip.i = clip.length - 1    # nothing is left to step and no head reads a row: the last turn runs what runs whole and ends the walk
                if not clip.length:
                    clip.ready.emit({}, 0, g.fps)
                clip.report()
            return "walk", [(clip, begin)]
        if clip.i < clip.length:
            if self._clip_on and chained:
                return "walk", [(clip, clip.turn)]
            return "walk", [(clip, clip.halt), (clip, clip.emit)]   # the chain over the rows it stopped at: the cadence's last result is short of them
        per = self._period
        if per.i < per.length:
            if self._clip_on and (sub := _walking(p, per.walked, per.cut)) is not None:
                per.plan = sub
                return "walk", [(per, per.turn)]
            self._legs.clear()
            return "walk", [(per, per.halt)]
        while self._clip_on and self._legs:
            nid, cut = self._legs.pop(0)
            if (sub := _walking(p, nid, cut)) is None:
                continue
            first, end = (min(r, count) for r in cut.extent.rows)
            ask = self._held(sub, nid, first, end)
            if ask is not None and ask[1]:
                continue

            def begin(sub=sub, nid=nid, cut=cut, first=first, end=end, ask=ask):
                per.plan, per.walked, per.cut, per.spared = sub, nid, cut, False
                per.given, per.handed = ({}, None) if ask is None else (ask[2], ask[3])
                per.begin(first, end - first, self._legs_by)
            return "walk", [(per, begin)]
        return None

    def _held(self, sub, nid, first, end):
        """What give_periods was told of the cut of rows `first` to `end` that the Plan `sub` walks
        from `nid`, where it is of the keys `sub` has; else None."""
        ask = self._held_periods.get((nid, (first, end)))
        if ask is None or ask[0] != period_keys(sub) or any(len(served) != end - first for served, _ in (ask[3] or {}).values()):
            return None
        return ask

    def _spared(self, p, nid, cut, count):
        """Whether every chain node's result over `cut`, walked from `nid` under the Plan `p`, is held."""
        sub = _walking(p, nid, cut)
        ask = None if sub is None else self._held(sub, nid, *(min(r, count) for r in cut.extent.rows))
        return ask is not None and ask[1]
