"""The one thread that runs tools: the ladder, a scrub, then the window walk, then the clip walk, and the
condition it waits on. Each rung is a job, _Scrub and two _Walk, holding its own state and doing one thing
with a turn; the GUI side sets a job's ask under the lock and the scheduler takes it and tells the job to
begin, once. The window walk keeps the densities, and each walk reports its rows to the probe in its own lane;
the clip walk runs behind a finished window so what is viewed never waits on it, and a frame change abandons it
and its rows. A stack holds images by shape, one row each, and tables in an object array, one table a row, so a
walked node handing out a table never reads as a graph changing shape; there is none without a series chain to
run, and either range stops at STACK_BYTES. Each row steps the chain's prefix, the nodes the plan says step,
once; the rest runs whole over the prefix's accumulated result at each cadence row."""
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QThread, Signal

from . import density
from .decoder import EndOfStream
from .graph import Cancelled, Memo, Series, fed_row, gated, nbytes
from .stream import ASKED, EDIT, GIVEN, HAND, SHAPE

STACK_BYTES = 512 << 20   # the most a walk's stack and stepped results, the window's or the clip's, may take, as nbytes counts them
STOP_PATIENCE_MS = 10_000  # how long stop() waits before saying on stderr what it is waiting for


def _stack_for(n, out):
    return np.empty(n, object) if out.dtype.fields is not None else np.empty((n,) + out.shape, out.dtype)


def _fits(stack, out):
    """Whether `out` is a row of `stack`: a table into an object stack, an image by shape and dtype."""
    if stack.dtype == object:
        return out.dtype.fields is not None
    return stack.shape[1:] == out.shape and stack.dtype == out.dtype


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


@dataclass
class _Stepped:
    """A stepping node's progress over a range: the key it is stepped under, the state its tool
    returned last, its result accumulated over `rows` rows, and the bytes the result holds."""
    key: str
    state: object = None
    fields: dict = field(default_factory=dict)
    rows: int = 0
    bytes: int = 0


@dataclass
class _Walk:
    """One range of the walk, the window's or the clip's: the graph it walks, what it was asked under
    and walked under, the rows it holds, and the signals its progress, chain result and refusal go out on."""
    graph: object
    name: str           # "window" or "clip": the lane its events are in
    every: int          # the cadence, in rows, at which the chain's result and the densities go out, and no oftener than tell_every
    progress: object    # Signal(int, int, int): rows done, rows in the range, and of those done the rows that ran
    ready: object       # Signal(object, int, float): the chain's {node: result}, start, fps
    refused: object     # Signal(str): the range closed short, and why
    failed: object      # Signal(int, str): a tool raised at this row, on this node
    densities: object = None    # Signal(object, int) the window's plane densities go out on; None, and the walk folds none
    plan: object = None # the Plan a turn runs under, set by whoever drives the walk before it: a turn reads the plan off no other
    asked: bool = False # set under the worker's lock by anything that restarts this range; the scheduler takes it
    by: str = ASKED     # what last set `asked`, one of stream.BEGUN_BY; the scheduler takes it with the ask
    tell_every: float = 0.0     # s between a turn's tellings of the rows done, the range's end always told; 0 tells of each row
    told: float = 0.0   # when a turn last told, on perf_counter
    sent: float = 0.0   # when the range began or show() last ran, on perf_counter
    ask: tuple = (0, 0, False, {})  # (start, length, spared, given) the range was asked over; the clip's is the clip
    spared: bool = False        # the chain's results over the range are held elsewhere: nothing is stacked or stepped and no result goes out
    given: dict = field(default_factory=dict)     # node -> (raw key, its result's fields over the range), held elsewhere: stepped nodes the walk does not step
    start: int = 0
    length: int = 0
    i: int = 0
    ran: int = 0        # of the rows done, those whose walked row a store did not hold: Graph.tally moved under it
    bytes: int = 0
    stack: object = None
    dens: dict = field(default_factory=dict)      # node -> (length, BINS) counts, for the planes the walk folds
    at: dict = field(default_factory=dict)        # node -> the rows of the range folded for it; one whose output is no plane is at the range's end, with no counts
    refolding: bool = False     # the range is walked and a refold is under way: a walk of its own in the stream, see refold()
    # fold id -> (the stack's buffer, rows, that head's own folding of the stack); the buffer is held, not
    # its id, since a freed buffer's address comes back for the next stack of the same shape
    folded: dict = field(default_factory=dict)
    stepped: dict = field(default_factory=dict)   # node -> _Stepped

    def begin(self, start, length, by=ASKED):
        """Starts over `length` rows from `start`, dropping every row held, and tells the probe a walk
        began and `by` what, or with no row to walk that the range it was short of is closed."""
        if (self.i < self.length or self.refolding) and not length:
            self.graph.progress(self.i, self.i, (self.bytes, STACK_BYTES))
        self.start, self.length = start, length
        self.sent = time.perf_counter()
        self.drop()
        if length:
            self.graph.began(start, length, by)

    def drop(self):
        self.i = self.ran = self.bytes = 0
        self.stack, self.dens, self.at, self.folded, self.stepped = None, {}, {}, {}, {}
        self.refolding = False

    def turn(self):
        g, p = self.graph, self.plan
        row = self.start + self.i
        if self.stale_given():
            self.given = {}      # the chain moved on from what was given: the range is walked for all of it
            self.drop()
            g.began(self.start, self.length, GIVEN)
            return
        read = not self.spared and any(h not in self.given for h in p.heads or [None])   # whether anything reads the walked node's row
        before = g.tally()
        out = np.asarray(g.walk_row(row, p)) if read else None
        ran = g.tally() != before
        stacked = bool(p.chain) and read     # without a chain to run nothing reads the stack, and the rows are not held
        if self.i and ((self.stack is not None) != stacked or (stacked and not _fits(self.stack, out))):
            self.drop()      # the nodes or the shape changed under the walk; start over
            g.began(self.start, self.length, SHAPE)
            return
        if not self.i:
            if stacked and self.length * nbytes(out) > STACK_BYTES:
                self.refuse(f"the {self.name}'s stack would be {self.length * nbytes(out) / 2**30:.1f} GB; "
                            f"{', '.join(p.heads)} do not share a fold()")
                return
            self.stack = _stack_for(self.length, out) if stacked else None
        if stacked:
            self.stack[self.i] = out
            self.bytes += nbytes(out)
        if not self.spared:
            self.step(self.i + 1)
        self.i += 1
        self.fold()
        self.ran += ran
        if self.bytes > STACK_BYTES:
            self.refuse(f"the {self.name}'s stack reached {self.bytes / 2**30:.1f} GB at row {row}; the rows walked stand")
            return
        if not self.tell_every or self.i == self.length or time.perf_counter() - self.told >= self.tell_every:
            self.told = time.perf_counter() if self.tell_every else 0.0
            self.report()
            g.progress(self.i, self.length, (self.bytes, STACK_BYTES))
        if self.i == self.length or (self.i % self.every == 0 and self.spaced()):
            self.emit()

    def spaced(self):
        """Whether `tell_every` has passed since the range began or its densities and chain result last went out."""
        return not self.tell_every or time.perf_counter() - self.sent >= self.tell_every

    def folding(self):
        """The nodes whose densities this range folds: what the graph was told the plot shows, on
        the window, and none on the clip or where nothing is walked."""
        return [] if self.densities is None or self.plan.walk is None else self.graph.folded(self.plan)

    def behind(self):
        """Whether a node the plot shows has a row of the range unfolded."""
        return any(self.at.get(nid, 0) < self.length for nid in self.folding())

    def fold(self):
        """Folds one row more of each node in folding() that is short of the range, each from where
        its own count stands, so a node the plot comes to show later is folded from the range's
        first row beside the rest. A node whose output is no plane is computed once and no more."""
        for nid in self.folding():
            r = self.at.get(nid, 0)
            if r >= self.length:
                continue
            v = self.graph.density(nid, self.start + r, self.plan)
            if v is None:
                self.at[nid] = self.length
                continue
            if nid not in self.dens:
                self.dens[nid] = np.zeros((self.length, density.BINS), np.uint32)
            self.dens[nid][r] = v
            self.at[nid] = r + 1

    def refold(self):
        """A turn of a range already walked while behind(): fold() alone, the chain's rows standing
        as they are. In the stream it is a walk of the same range begun by a hand, its progress the
        rows every node of folding() has, and it is closed where the plot leaves those nodes first."""
        g = self.graph
        if not self.refolding:
            g.began(self.start, self.length, HAND)
        self.fold()
        done = min((self.at.get(nid, 0) for nid in self.folding()), default=self.length)
        self.refolding = done < self.length
        g.progress(done, self.length, (self.bytes, STACK_BYTES))
        if not self.refolding or (done % self.every == 0 and self.spaced()):
            self.show()

    def show(self):
        self.sent = time.perf_counter()
        if self.densities is not None:
            self.densities.emit({nid: d[: self.at[nid]] for nid, d in self.dens.items()}, self.start)

    def step(self, rows):
        """Brings every node the plan steps up to `rows` of the range; one whose raw key is not the
        one it was stepped under starts over from the range's first row. A head is handed the stacked
        row through its own fold() when the stack holds the rows unfolded; a chain node what its
        source's share feeds under the source's band. What the
        walk was given is the plan's still, by stale_given(), which every caller asks first."""
        g, p = self.graph, self.plan
        chain = chain_of(p)
        heads, shared = set(p.heads), p.fold is not None
        bands = {nid: band for nid, _, _, band, _ in chain}
        stepping = [(nid, p.entries[nid], params, src) for nid, _, params, _, src in chain if p.entries[nid].steps]
        for nid, (key, fields) in self.given.items():
            if nid not in self.stepped:
                self.stepped[nid] = _Stepped(key, fields=fields, rows=self.length)
        for nid in [n for n in self.stepped if n not in {s[0] for s in stepping}]:
            self.bytes -= self.stepped.pop(nid).bytes
        for nid, e, params, src in stepping:
            held = self.stepped.get(nid)
            if held is None or held.key != e.raw_key:
                if held is not None:
                    self.bytes -= held.bytes
                held = self.stepped[nid] = _Stepped(e.raw_key)
            fold = None if shared or nid not in heads else getattr(e.tool, "fold", None)
            for r in range(held.rows, rows):
                if nid in heads:
                    row = self.stack[r] if fold is None else fold(self.stack[r])
                else:
                    up = self.stepped[src]
                    row = fed_row({f: a[r] for f, a in up.fields.items()}, bands[src])
                with g.demand("walk", nid), g.probe(nid, self.start + r, e.raw_key) as ev:
                    try:
                        held.state, share = e.tool.step(held.state, row, r, params)
                    except Exception as exc:
                        exc.sieve_node = nid
                        g.note(nid, f"raised stepping row {self.start + r}: {type(exc).__name__}: {exc}")
                        raise
                    ev[0], ev[1] = "step", sum(nbytes(v) for v in share.values())
                for f, v in share.items():
                    a = held.fields.get(f)
                    if a is None:
                        a = held.fields[f] = np.empty(self.length, object if isinstance(v, np.ndarray) else np.asarray(v).dtype)
                    a[r] = v
                held.rows = r + 1
                held.bytes += ev[1]
                self.bytes += ev[1]
            g.note(nid, "")

    def emit(self):
        if not self.i:
            return
        g = self.graph
        self.show()
        results = None
        if self.stale_given():
            return              # the next turn begins the range again without it
        if not self.spared and (self.stack is not None or self.given):
            self.step(self.i)
            stepped = {nid: {f: a[: self.i] for f, a in h.fields.items()} for nid, h in self.stepped.items()}
            results = run_chain(g, None if self.stack is None else self.stack[: self.i], self.start, self.i, self.folded, stepped, self.plan)
        if results is not None:
            self.ready.emit(results, self.start, g.fps)

    def stale_given(self):
        """Whether a node the walk was given a result for is no longer stepped under that result's key."""
        return any((e := self.plan.entries.get(nid)) is None or not e.steps or e.raw_key != key for nid, (key, _) in self.given.items())

    def halt(self):
        """Stopped: the rows it has stand, and the count says so, to the window and to the probe."""
        self.length = self.i
        self.report()
        self.graph.progress(self.i, self.length, (self.bytes, STACK_BYTES))

    def report(self):
        self.progress.emit(self.i, self.length, self.ran)

    def close(self):
        """Returns the exception the chain raised over the rows held, if it did, the range closed
        with its progress alone: the handlers that close on a tool's first raise must not raise on
        its second."""
        self.halt()
        try:
            self.emit()
        except Exception as exc:
            traceback.print_exc()
            return exc

    def refuse(self, why):
        exc = self.close()
        if exc is not None:
            self.failed.emit(self.start + self.i, getattr(exc, "sieve_node", ""))
        self.refused.emit(why)

    def cancelled(self):
        pass            # the graph moved on under the row: the next turn reads the new state

    def ended(self):
        exc = self.close()
        if exc is not None:
            self.failed.emit(self.start + self.i, getattr(exc, "sieve_node", ""))

    def raised(self, exc):
        row = self.start + self.i
        again = self.close()
        self.failed.emit(row, getattr(again, "sieve_node", getattr(exc, "sieve_node", "")))


def chain_of(p):
    """The Plan `p`'s chain as Graph.series_chain gives the current one's."""
    return [(nid, e.tool, dict(e.params), e.band, e.src) for nid in p.chain for e in [p.entries[nid]]]


def run_chain(graph, stack, start, done, folds, stepped=None, p=None):
    """The series chain of the Plan `p`, the graph's current one with none, over `stack`, the
    walked node's rows from `start`, `done` of them so far, with `folds` the stack's own cache of
    each head's folding and `stepped` the result accumulated over those rows for each node the
    walk stepped, which runs nothing here: {node: result}, each gated and keyed; None when there
    is no chain."""
    p = p or graph.snapshot()
    chain = chain_of(p)
    if not chain:
        return None
    results, feeds, fps = {}, {}, graph.fps
    heads, folded = set(p.heads), p.fold is not None
    key = {nid: e.key for nid, e in p.entries.items()}
    buffer = None if stack is None else stack.base if stack.base is not None else stack
    for nid, tool, params, band, src in chain:
        if stepped is not None and nid in stepped:
            results[nid], feeds[nid] = gated(stepped[nid], band)
            graph.note(nid, "")
            if isinstance(results[nid], dict):
                results[nid] = {**results[nid], "key": key[nid]}
            continue
        if nid in heads and stack is None:
            continue        # a head with nothing walked for it: its standing says why
        elif nid in heads:
            fold = None if folded else getattr(tool, "fold", None)
            if fold is not None:
                held = folds.get(id(fold))
                if held is None or held[0] is not buffer or held[1] != len(stack):
                    held = (buffer, len(stack), np.stack([fold(row) for row in stack]) if len(stack) else np.zeros((0, 0)))
                    folds[id(fold)] = held
            series = Series(stack if fold is None else held[2], key[src], start, fps)
        elif feeds.get(src) is not None:
            series = Series(feeds[src], key[src], start, fps)
        else:
            graph.note(nid, f"{src} handed out no signal")
            continue
        with graph.demand("walk", nid), graph.probe(nid, start + done - 1, key[nid]) as ev:
            try:
                results[nid], feeds[nid] = gated(tool.run(series, params), band)
            except Exception as exc:
                exc.sieve_node = nid
                graph.note(nid, f"raised over {done} rows from {start}: {type(exc).__name__}: {exc}")
                raise
            ev[1] = Memo._size(results[nid])
        graph.note(nid, "")
        if isinstance(results[nid], dict):
            results[nid] = {**results[nid], "key": key[nid]}   # beside its gate: what a tool that writes a file records
    return results


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
        the chain is not run; `given`, node to (raw key, fields over the window), it holds those
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
        """Halt the clip walk where it is; the rows it has stand."""
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
            return "walk", [(clip, clip.halt)]
        return None
