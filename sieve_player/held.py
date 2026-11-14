"""A document's held series: the runs its walks made, in one file beside the document, and what the
file is good under beside its keys. A run is a Run, (start, rows, {node: result}, bytes), a walk's
results over `rows` rows from `start` and what they hold. The file is the stamp and then a record a run, and
File pickles a run once however often it writes. Runs is the runs held and which of them a range is
served from, told the chain as a Chain. Imports nothing of sieve_player; the window says when a run
is held and written, and what the chain now is."""
import hashlib
import os
import pickle
from typing import NamedTuple

import numpy as np

EXT = ".series"
VERSION = 4
SAMPLE = 256    # the most rows per_row pickles


def path_for(document):
    """Where the held file of the document saved at `document` lives; None for one never saved."""
    return f"{document}{EXT}" if document else None


def tools_print(tools):
    """A digest of every .py file in the folders `tools`, name to module, were loaded from: a key
    names a tool and its params and never its code, so this is what sees a tool edited."""
    h = hashlib.sha1()
    for root in sorted({os.path.dirname(os.path.abspath(t.__file__)) for t in tools.values() if getattr(t, "__file__", None)}):
        for name in sorted(n for n in os.listdir(root) if n.endswith(".py")):
            h.update(name.encode())
            with open(os.path.join(root, name), "rb") as f:
                h.update(f.read())
    return h.hexdigest()


def stamp(video, tools_digest):
    """What a held file is good under: the footage's size and date, which its key does not see, and
    `tools_digest`, taken when the tools were loaded."""
    st = os.stat(video)
    return (VERSION, st.st_size, st.st_mtime_ns, tools_digest)


class Run(NamedTuple):
    """A walk's results over `rows` rows from `start`, node to result, and the bytes they hold.
    Equal to itself alone: its results are arrays, whose equality is not a truth value."""
    start: int
    rows: int
    results: dict
    size: int

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
    """A record for each of `runs` at `f`'s position; where each lies, (offset, length)."""
    at = []
    for start, rows, results, size in runs:
        record = (start, rows, {nid: {k: _flat(v, rows) for k, v in r.items()} for nid, r in results.items()}, size)
        was = f.tell()
        pickle.dump(record, f, protocol=pickle.HIGHEST_PROTOCOL)
        at.append((was, f.tell() - was))
    return at


class File:
    """The held file at `path` and what it is good under, `stamp`. It knows where the record of
    each run it has read or written lies, by the run's identity, so the interpreter's time in a
    write is the runs the file has not had and never those it has: a run is pickled once. One
    thread at a time may call it."""

    def __init__(self, path, stamp):
        self.path, self.stamp = path, stamp
        self._had = None        # [(run, offset, length)], the records at path in their order; None when what is there is not known to be good
        self._end = 0           # where the last good record ends: what lies past it is a write cut short

    def load(self):
        """The runs at the path under the stamp, up to the first record that does not read; [] for
        a file that is absent, does not read or was written under another."""
        self._had, had = None, []
        try:
            with open(self.path, "rb") as f:
                if pickle.load(f) != self.stamp:
                    return []
                self._had, self._end = had, f.tell()
                while True:
                    start, rows, results, size = pickle.load(f)
                    run = Run(start, rows, {nid: {k: _rows(v) for k, v in r.items()} for nid, r in results.items()}, size)
                    had.append((run, self._end, f.tell() - self._end))
                    self._end = f.tell()
        except Exception:       # the file's end, or a truncated or foreign pickle, which raises whatever its bytes spell
            return [run for run, _, _ in had]

    def write(self, runs):
        """Leaves `runs` at the path in their order, those the file has first: the new are added
        behind the file's when it has no other, and else the file is made again, whole or not at
        all, the records of the runs kept copied as bytes. OSError when it cannot, the file then
        taken as unknown and the next write made of every run."""
        had, self._had = self._had, None
        kept = [(run, at, n) for run, at, n in had or [] if any(run is r for r in runs)]
        new = [r for r in runs if all(r is not run for run, _, _ in kept)]
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
                    pickle.dump(self.stamp, f, protocol=pickle.HIGHEST_PROTOCOL)
                    if kept:
                        with open(self.path, "rb") as old:
                            for _, was, n in kept:
                                old.seek(was)
                                kept_at.append((f.tell(), n))
                                f.write(old.read(n))
                    at = _dump(f, new)
                    end = f.tell()
                os.replace(part, self.path)      # the old file is closed by here: an open reader refuses the replace on Windows
            finally:
                if os.path.exists(part):
                    os.remove(part)
            kept = [(run, *where) for (run, _, _), where in zip(kept, kept_at)]
        self._had, self._end = kept + [(run, *where) for run, where in zip(new, at)], end


class Chain(NamedTuple):
    """The series chain as the plan now has it: `keys`, node to key in the chain's order; `steps`,
    the nodes of it a walk steps; `plate`, the row space its results are in."""
    keys: dict
    steps: frozenset
    plate: object


def good(result, key, plate):
    """Whether `result` is a series node's result under `key` in the row space `plate`; never for
    a `key` of None, a node the plan does not have."""
    return (key is not None and isinstance(result, dict) and "signal" in result
            and result.get("key") == key and result.get("plate") == plate)


class Runs:
    """The runs held, oldest first, and which of them a range is served from. `limit` is the bytes
    they may take together, each value's counted by `size_of`. Iterates as its runs. A result
    handed out is cut from a run's and shares its arrays."""

    def __init__(self, limit, size_of):
        self.limit, self.size_of, self.all = limit, size_of, []

    def __iter__(self):
        return iter(self.all)

    def __len__(self):
        return len(self.all)

    def take(self, runs):
        """Holds `runs`, oldest first, and no other."""
        self.all = list(runs)

    def _earliest(self):
        return sorted(self.all, key=lambda run: (run.start, -run.rows))

    @staticmethod
    def _serves(results, chain):
        return bool(chain.keys) and all(good(results.get(nid), key, chain.plate) for nid, key in chain.keys.items())

    def hold(self, start, rows, results, chain):
        """Holds `results` as a run over `rows` rows from `start` when every chain node has `rows`
        rows in it, unless a run held covers its rows with every node it has under the same key
        and plate; whether the runs held changed. A run it so covers goes, and while the runs
        together pass the limit the oldest goes that is not the longest the chain is served by,
        one of keys the chain has left before any other."""
        nodes = list(chain.keys)
        if not nodes or not all(isinstance(r := results.get(nid), dict) and "signal" in r and len(r["signal"]) == rows for nid in nodes):
            return False

        def under(results):
            return {nid: (r.get("key"), r.get("plate")) for nid, r in results.items()}.items()
        kept = {nid: results[nid] for nid in nodes}
        keys = under(kept)
        if any(run.start <= start and start + rows <= run.start + run.rows and keys <= under(run.results) for run in self.all):
            return False
        was = self.all
        self.all = [run for run in self.all
                    if not (start <= run.start and run.start + run.rows <= start + rows and under(run.results) <= keys)]
        self.all.append(Run(start, rows, kept, sum(self.size_of(v) for r in kept.values() for v in r.values())))
        while len(self.all) > 1 and sum(run.size for run in self.all) > self.limit:
            serving = [run for run in self.all if self._serves(run.results, chain)]
            longest = max(serving or self.all, key=lambda run: run.rows)
            spare = [run for run in self.all if run is not longest]
            left = [run for run in spare if run not in serving]
            self.all.remove((left or spare)[0])
        return self.all != was

    def over(self, s, n, chain):
        """The chain's results over `n` rows from `s`, cut from the run that began earliest and
        covers them under the keys the chain now has; None with none."""
        for start, rows, results, _ in self._earliest():
            if start <= s and s + n <= start + rows and self._serves(results, chain):
                return {nid: rows_of(results[nid], rows, s - start, n) for nid in chain.keys}
        return None

    def part(self, s, n, chain):
        """What the runs have of the chain over `n` rows from `s` when none has all of it: the
        stepped nodes' results, under the keys they now have, cut from the one covering run that
        has the most of them; {} with none."""
        best = {}
        for start, rows, results, _ in self._earliest():
            if start <= s and s + n <= start + rows:
                has = {nid: rows_of(results[nid], rows, s - start, n) for nid, key in chain.keys.items()
                       if nid in chain.steps and good(results.get(nid), key, chain.plate)}
                if len(has) > len(best):
                    best = has
        return best

    def spans(self, chain):
        """The rows a range inside which `over` serves, as (start, rows) stretches in order, none
        touching the next: the union of the runs under the keys the chain now has."""
        spans = []      # says whether a row is served, never how many times
        for s, n in sorted((s, n) for s, n, results, _ in self.all if self._serves(results, chain)):
            if spans and s <= sum(spans[-1]):
                spans[-1] = (spans[-1][0], max(sum(spans[-1]), s + n) - spans[-1][0])
            else:
                spans.append((s, n))
        return spans

    def from_first_row(self, nid, key, plate):
        """The run from row 0 that reaches furthest with `nid`'s result under `key` in `plate`;
        None with none."""
        return max((run for run in self.all if run.start == 0 and good(run.results.get(nid), key, plate)), key=lambda run: run.rows, default=None)

    def beside(self, nid, key, plate, start, rows):
        """`nid`'s signal under `key` in `plate` over the rows the runs have outside the `rows`
        from `start`: [(signal, its first row, gate or None)], the run that began earliest first
        as `over` serves, and no row twice."""
        drawn, out = [(start, start + rows)], []
        for s, n, results, _ in self._earliest():
            if not good(h := results.get(nid), key, plate):
                continue
            gate, at = h.get("gate"), s
            for a, b in sorted(drawn) + [(s + n, s + n)]:
                if at < min(a, s + n):
                    out.append((h["signal"][at - s:min(a, s + n) - s], at,
                                None if gate is None else gate[at - s:min(a, s + n) - s]))
                at = max(at, b)
            drawn.append((s, s + n))
        return out


def _a_row(v, rows):
    # never a tuple: a Plate is as long as a run of two rows
    return isinstance(v, (np.ndarray, list)) and len(v) == rows


def rows_of(result, rows, at, n):
    """`result`, a series node's dict over `rows` rows, cut to `n` of them from `at`: every array
    or list of `rows` items is cut, and the rest, its key and plate among them, stand."""
    return {f: v[at:at + n] if _a_row(v, rows) else v for f, v in result.items()}


def per_row(result):
    """About the bytes one row of `result`, a series node's dict, takes in the file, from its first
    SAMPLE rows as a record holds them; 0.0 for one with no signal or no rows."""
    n = len(result["signal"]) if isinstance(result, dict) and "signal" in result else 0
    if not n:
        return 0.0
    k = min(n, SAMPLE)
    return len(pickle.dumps({f: _flat(v[:k], k) for f, v in result.items() if _a_row(v, n)}, protocol=pickle.HIGHEST_PROTOCOL)) / k
