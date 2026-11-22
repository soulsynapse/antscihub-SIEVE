"""A document's held series: the runs its walks made, in one file beside the document, good under
its keys alone. A run is a Run, (start, rows, {node: result}, bytes, cut, walked), a walk's
results over `rows` rows from `start` inside a cut, what they hold, and each walked node's rows they were
stepped over. The file is the stamp and then a record a run, and
File pickles a run once however often it writes. Runs is the runs held and which of them a range is
served from, a node at a time, told the chain as a Chain, and a node's values in a cut listed as a Listed; `marked` is the nodes whose held results were made under
other code than lies on disk. Imports nothing of sieve_player but cut; the window says when a run
is held and written, and what the chain now is."""
import os
import pickle
from typing import NamedTuple

import numpy as np

from .cut import read, reading

EXT = ".series"
VERSION = 7
SAMPLE = 256    # the most rows per_row pickles
COPY = 1 << 20  # the most bytes of a kept record in memory as the file is made again


def path_for(document):
    """Where the held file of the document saved at `document` lives; None for one never saved."""
    return f"{document}{EXT}" if document else None


STAMP = (VERSION,)      # what a file begins with: the form of its records, and nothing of the tools' code or the footage, which a run's keys name


def _stamped(said):
    """Whether `said`, what a file begins with, is a stamp of this form."""
    return said == STAMP


class Run(NamedTuple):
    """A walk's results over `rows` rows from `start`, node to result, the bytes they hold, and
    `cut`, (first row, row past the last) of the cut it was walked inside, None the whole footage,
    and `walked`, a (node, key, its `rows` rows) for each walked node the walk stacked, or None. `size`
    counts the walked rows too. Equal to itself alone: its results are arrays, whose equality is
    not a truth value."""
    start: int
    rows: int
    results: dict
    size: int
    cut: tuple | None = None
    walked: tuple | None = None

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    __hash__ = object.__hash__


_FLAT = "held:flat"


def _flat(v, rows):
    """`v` as a record holds it: an object array of `rows` arrays of one dtype and row shape as
    their concatenation and lengths, since pickle spends its time on the count of arrays and not
    their bytes; anything else as it is."""
    if not (isinstance(v, np.ndarray) and v.dtype == object and v.ndim == 1 and len(v) == rows and rows):
        return v
    kinds = {(a.dtype, a.shape[1:]) if isinstance(a, np.ndarray) and a.ndim and not a.dtype.hasobject else None for a in v}
    if len(kinds) != 1 or None in kinds:
        return v
    return (_FLAT, np.concatenate(list(v)), np.fromiter((len(a) for a in v), np.int64, rows))


def _rows(v):
    """What `_flat` made of a value, as the value was."""
    if not (isinstance(v, tuple) and len(v) == 3 and isinstance(v[0], str) and v[0] == _FLAT):
        return v
    _, flat, lengths = v
    ends = np.cumsum(lengths).tolist()
    out = np.empty(len(ends), object)
    for i, (a, b) in enumerate(zip([0, *ends[:-1]], ends)):
        out[i] = flat[a:b]
    return out


def _dump(f, runs):
    """A record for each of `runs` at `f`'s position; where each lies, (offset, length), a run
    that does not pickle leaving no record and lying at length 0."""
    at = []
    for start, rows, results, size, *more in runs:
        cut, walked = (*more, None, None)[:2]
        record = (start, rows, {nid: {k: _flat(v, rows) for k, v in r.items()} for nid, r in results.items()}, size, cut,
                  None if walked is None else tuple((*w[:2], _flat(w[2], rows)) for w in walked))
        was = f.tell()
        try:
            pickle.dump(record, f, protocol=pickle.HIGHEST_PROTOCOL)
        except (OSError, MemoryError):      # the machine's refusal and not the value's: the run is tried again
            raise
        except Exception:       # a value pickle refuses, which raises whatever the value does
            f.seek(was)
            f.truncate()
        at.append((was, f.tell() - was))
    return at


class File:
    """The held file at `path`. It knows where the record of
    each run it has read or written lies, by the run's identity, so the interpreter's time in a
    write is the runs the file has not had and never those it has: a run is pickled once. One
    thread at a time may call it."""

    def __init__(self, path):
        self.path = path
        self._had = None        # [(run, offset, length)], the records at path in their order; None when what is there is not known to be good
        self._end = 0           # where the last good record ends: what lies past it is a write cut short

    def load(self):
        """The runs at the path, up to the first record that does not read; [] for a file that is
        absent, does not read or begins with no stamp of this form."""
        self._had, had = None, []
        try:
            with open(self.path, "rb") as f:
                if not _stamped(pickle.load(f)):
                    return []
                self._had, self._end = had, f.tell()
                while True:
                    start, rows, results, size, cut, walked = pickle.load(f)
                    run = Run(start, rows, {nid: {k: _rows(v) for k, v in r.items()} for nid, r in results.items()}, size,
                              cut, None if walked is None else tuple((*w[:2], _rows(w[2])) for w in walked))
                    had.append((run, self._end, f.tell() - self._end))
                    self._end = f.tell()
        except Exception:       # the file's end, or a truncated or foreign pickle, which raises whatever its bytes spell
            return [run for run, _, _ in had]

    def write(self, runs):
        """Leaves `runs` at the path in their order, those the file has first: the new are added
        behind the file's when it has no other, and else the file is made again, whole or not at
        all, the records of the runs kept copied as bytes; of no runs it leaves a file that loads
        as none. Returns the runs that did not pickle:
        each is left out of the file and counted as had, so it is tried once and costs the others
        nothing. OSError when the file cannot be written and MemoryError when a run cannot be
        pickled for want of room, the file then taken as unknown and the next write made of every
        run."""
        had, self._had = self._had, None
        asked = {id(r) for r in runs}
        kept = [(run, at, n) for run, at, n in had or [] if id(run) in asked]
        has = {id(run) for run, _, _ in kept}
        new = [r for r in runs if id(r) not in has]
        if had is not None and len(kept) == len(had):
            with open(self.path, "r+b") as f:
                f.seek(self._end)
                f.truncate()
                at = _dump(f, new)
                end = f.tell()
        else:
            part, kept_at = f"{self.path}.part", []
            try:
                with open(part, "wb") as f:
                    pickle.dump(STAMP, f, protocol=pickle.HIGHEST_PROTOCOL)
                    if kept:
                        with open(self.path, "rb") as old:
                            for _, was, n in kept:
                                old.seek(was)
                                kept_at.append((f.tell(), n))
                                while n and (piece := old.read(min(n, COPY))):
                                    n -= f.write(piece)
                                if n:
                                    raise OSError(f"{self.path} ends inside a record it had")
                    at = _dump(f, new)
                    end = f.tell()
                os.replace(part, self.path)      # the old file is closed by here: an open reader refuses the replace on Windows
            finally:
                if os.path.exists(part):
                    os.remove(part)
            kept = [(run, *where) for (run, _, _), where in zip(kept, kept_at)]
        self._had, self._end = kept + [(run, *where) for run, where in zip(new, at)], end
        return [run for run, (_, n) in zip(new, at) if not n]


class Chain(NamedTuple):
    """The series chain as the plan now has it: `keys`, node to key in the chain's order; `steps`,
    the nodes of it a walk steps; `reach`, node to (rows before, rows after) a row that its result
    there reads, None a side without bound, as a node it does not name."""
    keys: dict
    steps: frozenset
    reach: dict = {}


class Listed(NamedTuple):
    """A node's values in a cut: `record`, the cut.Record they are of, and `parts`, (first row,
    result) in row order, each its result over a stretch of the cut's rows as one run serves it, no
    row twice and a row no run serves in none."""
    record: object
    parts: list


def _read(walk, cut, reach, s, n):
    """What a node's rows over `n` rows from `s` read, at their first row and their last, of a walk
    over `walk`, (first row, row past the last), inside a cut of rows `cut`, by cut.read."""
    return (read(walk, reach, s)[0], read(cut, reach, s)[0], read(walk, reach, s + n - 1)[1], read(cut, reach, s + n - 1)[1])


def _reads(walk, cut, reach, lo, hi):
    """`_read`'s four edges a row at a time over rows `lo` to `hi`, -1 where a row read none."""
    rows = np.arange(lo, hi)

    def edges(span):
        if span is None:
            return np.full(len(rows), -1), np.full(len(rows), -1)
        below, on_from = reading(span, reach)
        return np.where(rows < below, span[0], -1), np.where(rows >= on_from, span[1], -1)
    (wf, we), (cf, ce) = edges(walk), edges(cut)
    return wf, cf, we, ce


def good(result, key):
    """Whether `result` is a series node's result under `key`; never for a `key` of None, a node
    the plan does not have."""
    return key is not None and isinstance(result, dict) and "signal" in result and result.get("key") == key


class Runs:
    """The runs held, oldest first, and which of them a range is served from. `limit` is the bytes
    they may take together, each node's result counted by `size_of(node, result)`. Iterates as its runs. A result
    handed out is cut from a run's and shares its arrays."""

    def __init__(self, limit, size_of):
        self.limit, self.size_of, self.all = limit, size_of, []
        self._index = (None, None, None, 0)     # (`all` as indexed, each run's first row, its row past the last, their bytes together)

    def _indexed(self):
        """`_index` of the runs as they are: made again where `all` is another list or another length,
        so a caller that sets or takes `all` needs say nothing."""
        if self._index[0] is not self.all or len(self._index[1]) != len(self.all):
            rows = np.array([(run.start, run.start + run.rows) for run in self.all], np.int64).reshape(-1, 2)
            self._index = (self.all, rows[:, 0].copy(), rows[:, 1].copy(), sum(run.size for run in self.all))
        return self._index

    def _near(self, a, b):
        """The runs holding a row of `a` to `b`, oldest first, at the cost of those and not of every run."""
        runs, starts, ends, _ = self._indexed()
        return [runs[i] for i in np.flatnonzero((starts < b) & (a < ends)).tolist()]

    def __iter__(self):
        return iter(self.all)

    def __len__(self):
        return len(self.all)

    def take(self, runs):
        """Holds `runs`, oldest first, and no other."""
        self.all = list(runs)

    def _earliest(self, over=None):
        """The runs, the one that began earliest first; with `over`, (first row, row past the last),
        those alone that hold a row of it."""
        runs = self.all if over is None else self._near(*over)
        return sorted(runs, key=lambda run: (run.start, -run.rows))

    @staticmethod
    def _has(results, chain):
        """The chain's nodes whose result in `results` is good under the key it now has: what
        every reader here and the limit take a run to be worth."""
        return [nid for nid, key in chain.keys.items() if good(results.get(nid), key)]

    @staticmethod
    def _whole(results, chain):
        return bool(chain.keys) and len(Runs._has(results, chain)) == len(chain.keys)

    @staticmethod
    def _serves(run, nid, s, n, walk, cut, chain):
        """Whether `run` serves `nid`'s rows over `n` rows from `s` to a walk over `walk` inside a cut
        of rows `cut`: it covers them under the key the node now has, and they read the same of its
        walk and cut as of those."""
        reach = chain.reach.get(nid, (None, None))
        return (run.start <= s and s + n <= run.start + run.rows and good(run.results.get(nid), chain.keys.get(nid))
                and _read((run.start, run.start + run.rows), run.cut, reach, s, n) == _read(walk, cut, reach, s, n))

    def _serving(self, s, n, chain, walk, cut, nodes):
        """Node of `nodes` to its result over `n` rows from `s`, cut from the run that began earliest
        and serves it, for each one served."""
        out = {}
        for run in self._earliest((s, s + n)):
            for nid in nodes:
                if nid not in out and self._serves(run, nid, s, n, walk, cut, chain):
                    out[nid] = rows_of(run.results[nid], run.rows, s - run.start, n)
        return out

    def hold(self, start, rows, results, chain, cut=None, worth=None, walked=None):
        """Holds `results` as a run over `rows` rows from `start` inside a cut of rows `cut` when every
        chain node has `rows` rows in it under a key, unless a run held serves every node it has over
        its rows under the same key and its walk and cut, and holds the walked rows if it has them.
        Returns the rows, (first, row past the last), of each run that went or came, none where the
        runs held did not change. `walked` is a (node, key, its rows, the bytes they hold) for
        each walked node, or None. A run it so serves goes unless it holds walked rows it does not, and while the runs
        together pass the limit the oldest goes that is not the one
        `worth`, a Chain and `chain` with none, has most of, a run it has nothing of before any other.
        What it has of a run is the run's rows for each node of `_has`, the longer run of two it has
        as much of and the one held last of two as long. The last run stays whatever it takes."""
        nodes = list(chain.keys)
        if not nodes or not all(isinstance(r := results.get(nid), dict) and "signal" in r and len(r["signal"]) == rows
                                and r.get("key") is not None for nid in nodes):
            return False

        def stands_in(over, run):
            within = Chain({nid: r.get("key") for nid, r in run.results.items()}, chain.steps, chain.reach)
            return all(self._serves(over, nid, run.start, run.rows, (run.start, run.start + run.rows), run.cut, within)
                       for nid in within.keys)
        kept = {nid: results[nid] for nid in nodes}
        new = Run(start, rows, kept, sum(self.size_of(nid, r) for nid, r in kept.items()) + sum(w[3] for w in walked or ()),
                  cut, None if walked is None else tuple(tuple(w[:3]) for w in walked))
        near = self._near(start, start + rows)      # a run that serves the new one, or that it serves, holds a row of it
        if any(stands_in(run, new) and (new.walked is None or run.walked is not None) for run in near):
            return False
        gone = [run for run in near if stands_in(new, run) and not (run.walked is not None and new.walked is None)]
        if gone:
            self.all = [run for run in self.all if not any(run is g for g in gone)]
        runs, starts, ends, size = self._indexed()
        runs.append(new)
        self._index = (runs, np.append(starts, start), np.append(ends, start + rows), size + new.size)
        came = [new]
        while len(self.all) > 1 and self._indexed()[3] > self.limit:
            has = {run: len(self._has(run.results, worth or chain)) * run.rows for run in self.all}
            most = max(reversed(self.all), key=lambda run: (has[run], run.rows))
            spare = [run for run in self.all if run is not most]
            left = [run for run in spare if not has[run]]
            out = (left or spare)[0]
            (came.clear if out is new else lambda: gone.append(out))()
            self.all = [run for run in self.all if run is not out]
        return [(run.start, run.start + run.rows) for run in (*gone, *came)]

    def over(self, s, n, chain, walk, cut=None):
        """The chain's results over `n` rows from `s` to a walk over `walk`, (first row, row past the
        last), inside a cut of rows `cut`: each node's cut from the run that began earliest and
        serves it; None where a node has none."""
        got = self._serving(s, n, chain, walk, cut, chain.keys)
        return got if chain.keys and len(got) == len(chain.keys) else None

    def part(self, s, n, chain, walk, cut=None):
        """The stepped nodes' results that `over` would serve, each node's its own: rows a walk over
        `walk` can step the rest from as it would its own; {} with none."""
        return self._serving(s, n, chain, walk, cut, [nid for nid in chain.keys if nid in chain.steps])

    def walked_rows(self, nid, key, reach, s, n, walk, cut=None):
        """The walked node `nid`'s rows under `key` over `n` rows from `s` to a walk over `walk`
        inside a cut of rows `cut`, as `serves` serves a series node's, a row at a time from the run
        that began earliest whose row read the same of its walk and cut, `reach` the node's:
        (a bool array of which of the `n` rows are served, an object array of them), as
        walk._Walk.handed takes them."""
        out, have = np.empty(n, object), np.zeros(n, bool)
        want = _reads(walk, cut, reach, s, s + n)
        for run in self._earliest((s, s + n)):
            rows = next((w[2] for w in run.walked or () if w[:2] == (nid, key)), None)
            if rows is None:
                continue
            a, b = max(s, run.start), min(s + n, run.start + run.rows)
            if a >= b:
                continue
            got = _reads((run.start, run.start + run.rows), run.cut, reach, a, b)
            ok = ~have[a - s:b - s] & np.all([g == w[a - s:b - s] for g, w in zip(got, want)], axis=0)
            for i in np.flatnonzero(ok).tolist():
                out[a - s + i] = rows[a - run.start + i]
            have[a - s:b - s] |= ok
        return have, out

    def listed(self, nid, chain, record, count):
        """`nid`'s values in the cut `record`, a cut.Record, as a Listed: its rows, or the footage's
        `count` rows for a record of every row, each served to a walk of the cut from its
        first row to its last from the run that began earliest and serves it, whatever the value
        read of the cut, so a row may be served by a run of another cut."""
        cut = record.extent.rows
        walk = cut or (0, count)
        before, after = chain.reach.get(nid, (None, None))
        near = self._earliest(walk)     # a run holding no row of the cut serves none of it, and where it lies moves no part
        spans = [walk, *((run.start, run.start + run.rows) for run in near), *(run.cut for run in near if run.cut)]
        marks = {m for span in spans for m in span}
        marks |= {f + before for f, _ in spans} if before is not None else set()
        marks |= {e - after for _, e in spans} if after is not None else set()
        points = sorted(m for m in marks if walk[0] <= m <= walk[1])     # between two, what a row reads of every edge is one
        parts = []
        for a, b in zip(points, points[1:]):
            run = next((run for run in near if self._serves(run, nid, a, b - a, walk, cut, chain)), None)
            if run is not None and parts and parts[-1][2] is run and parts[-1][1] == a:
                parts[-1][1] = b
            elif run is not None:
                parts.append([a, b, run])
        return Listed(record, [(a, rows_of(run.results[nid], run.rows, a - run.start, b - a)) for a, b, run in parts])

    def spans(self, chain):
        """The rows held under the keys the chain now has, as (start, rows) stretches in order,
        none touching the next: the union of those runs. `over` serves a range inside one run,
        so one that lies in a stretch across two is not served."""
        spans = []      # says whether a row is served, never how many times
        for s, n in sorted((run.start, run.rows) for run in self.all if self._whole(run.results, chain)):
            if spans and s <= sum(spans[-1]):
                spans[-1] = (spans[-1][0], max(sum(spans[-1]), s + n) - spans[-1][0])
            else:
                spans.append((s, n))
        return spans

    def from_first_row(self, nid, key):
        """The run from row 0 that reaches furthest with `nid`'s result under `key`;
        None with none."""
        return max((run for run in self.all if run.start == 0 and good(run.results.get(nid), key)), key=lambda run: run.rows, default=None)

    def beside(self, nid, key, start, rows):
        """`nid`'s signal under `key` over the rows the runs have outside the `rows`
        from `start`: [(signal, its first row, gate or None)], the run that began earliest first
        as `over` serves, and no row twice."""
        out, reached = [], 0     # reached: the row past the last an earlier run drew, each beginning no later than the next
        for s, n, results, *_ in self._earliest():
            if not good(h := results.get(nid), key):
                continue
            gate, at = h.get("gate"), max(s, reached)
            for a, b in ((start, start + rows), (s + n, s + n)):
                if at < min(a, s + n):
                    out.append((h["signal"][at - s:min(a, s + n) - s], at,
                                None if gate is None else gate[at - s:min(a, s + n) - s]))
                at = max(at, b)
            reached = max(reached, s + n)
        return out


def marked(runs, chain, now, above):
    """The nodes whose results held in `runs` under the keys of `chain` are to be said stale.
    `now` is node to the digest of its tool's code as it lies, of every node whose tool runs and
    has one; `above`, node to the nodes it reads. A run's result for a chain node says under
    "code" what it was made under, node to digest over the node and those above it: a node of
    `now`, at or above a chain node whose result is good under its key, is marked where that
    result says another digest of it or none, and with it every node below one marked. A result
    under a key the chain has left marks nothing."""
    out = set()
    for _, _, results, *_ in runs:
        for nid in Runs._has(results, chain):
            made = results[nid].get("code") or {}
            todo, seen = [nid], set()
            while todo:
                n = todo.pop()
                if n in seen:
                    continue
                seen.add(n)
                if n in now and made.get(n) != now[n]:
                    out.add(n)
                todo += above.get(n, ())
    while more := {n for n, ups in above.items() if n not in out and any(u in out for u in ups)}:
        out |= more
    return out


def _a_row(v, rows):
    return isinstance(v, (np.ndarray, list)) and len(v) == rows


def rows_of(result, rows, at, n):
    """`result`, a series node's dict over `rows` rows, cut to `n` of them from `at`: every array
    or list of `rows` items is cut, and the rest, its key among them, stand."""
    return {f: v[at:at + n] if _a_row(v, rows) else v for f, v in result.items()}


UNITS = ("B", "KB", "MB", "GB", "TB")


def in_units(n):
    """(figure, unit): `n` bytes as the shortest figure, to one decimal past B, in the first of UNITS that holds it under 1024, or the last."""
    for unit in UNITS[:-1]:
        if n < 1024:
            break
        n /= 1024
    else:
        unit = UNITS[-1]
    return (f"{n:.0f}" if unit == "B" else f"{n:.1f}"), unit


def per_row(result):
    """About the bytes one row of `result`, a series node's dict, takes in the file, from its first
    SAMPLE rows as a record holds them; 0.0 for one with no signal or no rows."""
    n = len(result["signal"]) if isinstance(result, dict) and "signal" in result else 0
    if not n:
        return 0.0
    k = min(n, SAMPLE)
    return len(pickle.dumps({f: _flat(v[:k], k) for f, v in result.items() if _a_row(v, n)}, protocol=pickle.HIGHEST_PROTOCOL)) / k
