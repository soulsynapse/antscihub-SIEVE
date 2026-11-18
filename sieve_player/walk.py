"""A walk of one range, the window's or the clip's, and the series chain run over its rows. It imports no Qt:
the signals a walk tells through are handed to it, so the worker's thread turns one and bare.py drives one alone.
The window walk keeps the densities, and each walk reports its rows to the probe in its own lane. A stack holds
images by shape, one row each, and tables in an object array, one table a row, so a walked node handing out a
table never reads as a graph changing shape; there is none without a series chain to run, and either range stops
at STACK_BYTES. Each row steps the chain's prefix, the nodes the plan says step, once; the rest runs whole over
the prefix's accumulated result at each cadence row."""
import time
import traceback
from dataclasses import dataclass, field

import numpy as np

from . import density
from .registry import fold_of, imported_print
from .graph import Series, gated, inband
from .stream import ASKED, GIVEN, HAND, SHAPE
from .wire import ROWS, is_table, nbytes, own_bytes, share_bytes

STACK_BYTES = 512 << 20   # the most a walk's stack and stepped results, the window's or the clip's, may take, as nbytes counts them


def _stack_for(n, out, table):
    return np.empty(n, object) if table else np.empty((n,) + out.shape, out.dtype)


def _fits(stack, out, table):
    """Whether `out` is a row of `stack`, `table` saying whether the walked node hands out one: a
    table into an object stack, an image by shape and dtype."""
    if stack.dtype == object:
        return table
    return not table and stack.shape[1:] == out.shape and stack.dtype == out.dtype


@dataclass
class _Stepped:
    """A stepping node's progress over a range: the key it is stepped under, the state its tool
    returned last, its result accumulated over `rows` rows, and the bytes the result holds; beside
    it what graph.gated makes of that result, `gate` and `fed` over the first `gated` rows under
    `band`, None for a result with no signal. `table` is whether the node's type is a table.
    `given` is whether the result was held elsewhere and handed in, `code` then what it was made
    under as that result said it, None for one that said nothing."""
    key: str
    table: bool = False
    given: bool = False
    code: object = None
    state: object = None
    fields: dict = field(default_factory=dict)
    rows: int = 0
    bytes: int = 0
    band: object = None
    gated: int = 0
    gate: object = None
    fed: object = None
    empty: object = None    # the one emptied table every gated-out row of a table type's result feeds

    def regate(self, band):
        """Brings `gate` and `fed` up to `rows` under `band`: from the row they reached under the
        same band, from the first under another, since the band is not in the key stepped under."""
        signal = self.fields.get("signal")
        if signal is None:
            return
        if band != self.band:
            self.band, self.gated = band, 0
        lo, hi = self.gated, self.rows
        if lo >= hi:
            return
        tables = self.fields[ROWS] if self.table else None
        if self.gate is None:
            self.gate = np.ones(len(signal), bool)
            self.fed = np.empty(len(signal), object) if tables is not None else np.zeros(len(signal), signal.dtype)
        kept = np.ones(hi - lo, bool) if band is None else inband(signal[lo:hi], band)
        self.gate[lo:hi] = kept
        if tables is not None:
            self.fed[lo:hi] = tables[lo:hi]
            if self.empty is None:
                self.empty = tables[lo][:0]
            for r in np.flatnonzero(~kept):
                self.fed[lo + r] = self.empty
        else:
            self.fed[lo:hi] = np.where(kept, signal[lo:hi], np.zeros((), signal.dtype))
        self.gated = hi

    def upto(self, rows):
        """The result over its first `rows` rows as graph.gated hands it out, and what it feeds."""
        result = {f: a[:rows] for f, a in self.fields.items()}
        if self.given:
            result["code"] = self.code
        if self.gate is None:
            return result, None
        return {**result, "gate": self.gate[:rows]}, self.fed[:rows]


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
    given: dict = field(default_factory=dict)     # node -> (raw key, its result's fields over the range, the code it was made under or None), held elsewhere: stepped nodes the walk does not step
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
        self.graph.rests()
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
        of = None if p.fold is not None or p.walk not in p.entries else p.entries[p.walk].produces    # a folded row is of no type
        if self.i and ((self.stack is not None) != stacked or (stacked and not _fits(self.stack, out, is_table(of)))):
            self.drop()      # the nodes or the shape changed under the walk; start over
            g.began(self.start, self.length, SHAPE)
            return
        if not self.i:
            if stacked and self.length * nbytes(of, out) > STACK_BYTES:
                self.refuse(f"the {self.name}'s stack would be {self.length * nbytes(of, out) / 2**30:.1f} GB; "
                            f"{', '.join(p.heads)} do not share a fold()")
                return
            self.stack = _stack_for(self.length, out, is_table(of)) if stacked else None
        if stacked:
            self.stack[self.i] = out
            self.bytes += nbytes(of, out)
        if not self.spared:
            self.step(self.i + 1)
        self.i += 1
        if self.i == self.length:
            g.rests()
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
        for nid, (key, fields, code) in self.given.items():
            if nid not in self.stepped:
                self.stepped[nid] = _Stepped(key, is_table(p.entries[nid].produces), given=True, code=code, fields=fields, rows=self.length)
        for nid in [n for n in self.stepped if n not in {s[0] for s in stepping}]:
            self.bytes -= self.stepped.pop(nid).bytes
        for nid, e, params, src in stepping:
            held = self.stepped.get(nid)
            if held is None or held.key != e.raw_key:
                if held is not None:
                    self.bytes -= held.bytes
                held = self.stepped[nid] = _Stepped(e.raw_key, is_table(e.produces))
            fold = None if shared or nid not in heads else fold_of(e.tool)
            for r in range(held.rows, rows):
                if nid in heads:
                    row = self.stack[r] if fold is None else fold(self.stack[r])
                else:
                    up = self.stepped[src]
                    row = None if up.fed is None else up.fed[r]
                with g.demand("walk", nid), g.probe(nid, self.start + r, e.raw_key) as ev:
                    try:
                        held.state, share = e.tool.step(held.state, row, r, params)
                    except Exception as exc:
                        exc.sieve_node = nid
                        g.note(nid, f"raised stepping row {self.start + r}: {type(exc).__name__}: {exc}")
                        raise
                    ev[0], ev[1] = "step", share_bytes(e.produces, share)
                for f, v in share.items():
                    a = held.fields.get(f)
                    if a is None:
                        a = held.fields[f] = np.empty(self.length, object if isinstance(v, np.ndarray) else np.asarray(v).dtype)
                    a[r] = v
                held.rows = r + 1
                held.bytes += ev[1]
                self.bytes += ev[1]
            held.regate(bands[nid])
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
            stepped = {nid: h.upto(self.i) for nid, h in self.stepped.items()}
            results = run_chain(g, None if self.stack is None else self.stack[: self.i], self.start, self.i, self.folded, stepped, self.plan)
        if results is not None:
            self.ready.emit(results, self.start, g.fps)

    def stale_given(self):
        """Whether a node the walk was given a result for is no longer stepped under that result's key."""
        return any((e := self.plan.entries.get(nid)) is None or not e.steps or e.raw_key != key for nid, (key, *_) in self.given.items())

    def halt(self):
        """Stopped: the rows it has stand, and the count says so, to the window and to the probe."""
        self.length = self.i
        self.graph.rests()
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
    return [(nid, e.tool, dict(e.computed), e.band, e.src) for nid in p.chain for e in [p.entries[nid]]]



def ran_above(p, nid):
    """Node to imported_print over `nid` and every node above it in the Plan `p` whose tool ran to
    feed it: none above a node that serves a file, nor that node, and none whose tool discover
    did not import."""
    out, todo, seen = {}, [nid], set()
    while todo:
        n = todo.pop()
        e = p.entries.get(n)
        if e is None or n in seen or e.file is not None:
            continue
        seen.add(n)
        if (d := imported_print(e.tool)) is not None:
            out[n] = d
        todo += [s for s in e.srcs.values() if s is not None]
    return out


def run_chain(graph, stack, start, done, folds, stepped=None, p=None):
    """The series chain of the Plan `p`, the graph's current one with none, over `stack`, the
    walked node's rows from `start`, `done` of them so far, with `folds` the stack's own cache of
    each head's folding and `stepped`, for each node the walk stepped, which runs nothing here,
    its result over those rows gated and what it feeds, as graph.gated would make them:
    {node: result}, each gated and keyed; None when there is no chain. A result that is a dict
    says under "code" what it was made under, node to imported_print over the node and every node
    above it whose tool ran: a head's by ran_above, any other's what its source's result says and
    its own, and a result handed in what it said where it was held; None where that or a source's
    said nothing."""
    p = p or graph.snapshot()
    chain = chain_of(p)
    if not chain:
        return None
    results, feeds, fps = {}, {}, graph.fps
    heads, folded = set(p.heads), p.fold is not None
    key = {nid: e.key for nid, e in p.entries.items()}
    buffer = None if stack is None else stack.base if stack.base is not None else stack

    def made(nid, src, handed_in=False):
        if handed_in:
            return results[nid]["code"]
        if nid in heads:
            return ran_above(p, nid)
        up = results[src].get("code") if isinstance(results.get(src), dict) else None
        own = imported_print(p.entries[nid].tool)
        return None if up is None else {**up, **({} if own is None else {nid: own})}

    for nid, tool, params, band, src in chain:
        if stepped is not None and nid in stepped:
            results[nid], feeds[nid] = stepped[nid]
            graph.note(nid, "")
            if isinstance(results[nid], dict):
                results[nid] = {**results[nid], "key": key[nid], "code": made(nid, src, "code" in results[nid])}   # _Stepped.upto says it of a result handed in alone
            continue
        if nid in heads and stack is None:
            continue        # a head with nothing walked for it: its standing says why
        elif nid in heads:
            fold = None if folded else fold_of(tool)
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
                results[nid], feeds[nid] = gated(tool.run(series, params), band, p.entries[nid].produces)
            except Exception as exc:
                exc.sieve_node = nid
                graph.note(nid, f"raised over {done} rows from {start}: {type(exc).__name__}: {exc}")
                raise
            ev[1] = own_bytes(results[nid])
        graph.note(nid, "")
        if isinstance(results[nid], dict):
            results[nid] = {**results[nid], "key": key[nid], "code": made(nid, src)}   # the key beside its gate: what a tool that writes a file records
    return results
