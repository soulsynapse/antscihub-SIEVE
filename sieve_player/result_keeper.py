"""A frame node's small rows in memory, by address: a Graph handed a Keeper asks it on a memo miss
and tells it each row it made. Only rows that are no image (ndim < 2 arrays, tables, scalars) of
frame nodes that are not static, served or stepped are kept. It has no disk of its own: a
document's checkpoint (held.File) lends it the chunks it carries and takes through `kept` those it
lacks, and a bare walk hands back what its Keeper holds, which the player's `take`s.
"""
import hashlib
import threading

import numpy as np

from .wire import nbytes

CHUNK = 256         # rows a chunk holds; in every address's name


def keepable(row):
    """Whether a row made is of a shape the keeper keeps: no image, no reference to another store's array."""
    return (isinstance(row, np.ndarray) and row.ndim < 2) or isinstance(row, (np.generic, int, float))


class Keeper:
    """The small rows walks made or were lent, as {(address key, chunk): {row: value}}, `limit`
    bytes of them by wire.nbytes, None no bound: past it no chunk is begun and none taken, and none
    held is let go. An address is the row's raw key, which holds the footage as
    decoder.footage_print samples it, the code of every tool above as discover imported it and the
    params, with the cut's rows and the node's reach: footage changed only where that print does
    not sample it is taken for the one before, and nothing of the player's own code or its
    libraries is in it. A chunk lent or taken is whole as it came, and one made here when it has
    every row of its CHUNK the cut holds, so one of a node walked uncut that ends the footage is
    never whole. Any thread, each call short under its lock."""

    def __init__(self, limit=None):
        self.limit, self._bytes = limit, 0
        self._chunks = {}           # (key, chunk) -> {row: value}
        self._spans = {}            # (key, chunk) -> (first row, row past the last) of the rows it is whole with
        self._waiting = set()       # the chunks made or taken that no `kept` has handed out
        self._addresses = {}
        self._lock = threading.Lock()

    def ask(self, e, row, cut):
        """`e`'s row `row` in `cut` as a walk kept it or a checkpoint lent it, read-only, or None."""
        with self._lock:
            a = self._address(e, row, cut)
            return None if a is None else self._chunks.get(a, {}).get(row)

    def made(self, e, row, cut, value):
        """`value` is what `e` made at `row` in `cut`, as the memo holds it, read-only."""
        if not keepable(value):
            return
        with self._lock:
            a = self._address(e, row, cut)
            if a is None:
                return
            rows = self._chunks.get(a)
            if rows is None:
                if self.limit is not None and self._bytes >= self.limit:
                    return
                rows = self._chunks[a] = {}
                self._waiting.add(a)
            if row not in rows:
                rows[row] = value
                self._bytes += nbytes(None, value)

    def lend(self, chunks):
        """Answers from `chunks`, (address key, chunk) to {row: value} as held.File.chunks has
        them, where they are rows of that chunk; a checkpoint's, which `kept` hands out again only
        to a checkpoint that lacks them."""
        self._add(chunks, waiting=False)

    def take(self, chunks):
        """Answers from `chunks`, as `lend` takes them, that no checkpoint has had: a bare walk's."""
        self._add(chunks, waiting=True)

    def waiting(self):
        """Whether a chunk made or taken has not been handed out by `kept`."""
        with self._lock:
            return bool(self._waiting)

    def kept(self, had=(), short=False):
        """(address key, chunk, rows) of each chunk held that is none of `had`, (key, chunk) pairs,
        whole, or with `short` whatever its rows: a copy of the rows held as it is handed. A
        generator, so what is not taken is not copied."""
        had = set(had)
        with self._lock:
            self._waiting -= had
            todo = sorted(self._chunks.keys() - had)
        for a in todo:
            with self._lock:
                rows = self._chunks[a]
                lo, hi = self._spans[a]
                if not (short or len(rows) >= hi - lo):
                    continue
                rows = dict(rows)
                self._waiting.discard(a)
            yield (*a, rows)

    def _add(self, chunks, waiting):
        took = {}
        for (key, chunk), rows in chunks.items():
            if isinstance(key, str) and isinstance(chunk, int) and isinstance(rows, dict) and all(
                    isinstance(r, int) and r // CHUNK == chunk and keepable(v) for r, v in rows.items()):
                for v in rows.values():
                    if isinstance(v, np.ndarray):
                        v.setflags(write=False)
                took[(key, chunk)] = rows
        with self._lock:
            for a, rows in took.items():
                held = self._chunks.get(a)
                if held is None:
                    if self.limit is not None and self._bytes >= self.limit:
                        continue
                    held = self._chunks[a] = {}
                self._spans[a] = (0, 0)
                new = {r: v for r, v in rows.items() if r not in held}
                held.update(new)
                self._bytes += sum(nbytes(None, v) for v in new.values())
                if waiting and new:
                    self._waiting.add(a)

    def _address(self, e, row, cut):
        if e.kind != "frame" or e.static or e.file is not None or e.steps:
            return None
        rows = None if cut.extent.rows is None else tuple(cut.extent.rows)
        at = (e.raw_key, rows, e.reach)
        key = self._addresses.get(at)
        if key is None:
            key = self._addresses[at] = hashlib.sha1(repr(at).encode()).hexdigest()[:24] + f"-{CHUNK}rows"
        a = (key, row // CHUNK)
        if a not in self._spans:
            lo, hi = a[1] * CHUNK, (a[1] + 1) * CHUNK
            self._spans[a] = (lo, hi) if rows is None else (max(lo, rows[0]), min(hi, rows[1]))
        return a
