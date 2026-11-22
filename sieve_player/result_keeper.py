"""A frame node's small rows on their way to and from a document's checkpoint, by an address that is
the same in another session. It holds no row: a Graph's memo holds those made and lent, and the
Graph builds its Keeper over that memo, asks it on a memo miss and tells it each row a tool made.
Only rows that are no image (ndim < 2 arrays, tables, scalars) of frame nodes that are not static,
served or stepped have an address. A checkpoint (held.File) lends the chunks it carries and takes
through `kept` those it lacks, read from the memo as they are handed; a bare walk's `kept` is what
the player `take`s.
"""
import hashlib
import threading

import numpy as np

from .wire import nbytes

CHUNK = 256         # rows a chunk holds; in every address's name


def keepable(row):
    """Whether a row made is of a shape a checkpoint carries: no image, no reference to another store's array."""
    return (isinstance(row, np.ndarray) and row.ndim < 2) or isinstance(row, (np.generic, int, float))


class Keeper:
    """Which of `memo`'s entries a checkpoint carries, by (address key, chunk). An address is the
    row's raw key, which holds the footage as decoder.footage_print samples it, and the params, with the cut's rows and the node's reach:
    footage changed only where that print does not sample it is taken for the one before, and
    nothing of the player's own code or its libraries is in it. `key_of((raw key, cut rows, reach),
    row)` is the memo key a row of that address is held under. A chunk lent or taken is held in the
    memo's lent tier, whole as it came, until the memo lets it go; one made here is whole when the
    memo holds every row of its CHUNK the cut holds, so one of a node walked uncut that ends the
    footage is never whole. A row the memo let go is not handed out. Any thread, each call short
    under its lock and the memo's."""

    def __init__(self, memo, key_of):
        self.memo, self.key_of = memo, key_of
        self._chunks = set()        # (key, chunk) made, lent or taken
        self._spans = {}            # (key, chunk) -> (first row, row past the last) of the rows it is whole with
        self._waiting = set()       # the chunks made or taken that no `kept` has handed out
        self._addresses, self._at = {}, {}      # (raw key, cut rows, reach) <-> address key
        self._lock = threading.Lock()

    def ask(self, e, row, cut):
        """`e`'s row `row` in `cut` as a checkpoint or a bare walk lent it, read-only, or None."""
        with self._lock:
            a = self._address(e, row, cut)
        return None if a is None else self.memo.lent(a, row)

    def made(self, e, row, cut, value):
        """`value` is what `e` made at `row` in `cut`, which the memo holds under its key."""
        if not keepable(value):
            return
        with self._lock:
            a = self._address(e, row, cut)
            if a is not None and a not in self._chunks:
                self._chunks.add(a)
                self._waiting.add(a)

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
        """(address key, chunk, rows) of each chunk that is none of `had`, (key, chunk) pairs,
        whole, or with `short` whatever its rows the memo still holds: the rows as the memo holds
        them as each is handed, never pickled under a lock. A generator, so what is not taken is
        not read."""
        had = set(had)
        with self._lock:
            self._waiting -= had
            todo = sorted(self._chunks - had)
        for a in todo:
            with self._lock:
                (lo, hi), at = self._spans[a], self._at.get(a[0])
            rows = self.memo.lent(a) or {}
            if at is not None:
                keys = {self.key_of(at, r): r for r in range(*((lo, hi) if lo < hi else (a[1] * CHUNK, (a[1] + 1) * CHUNK))) if r not in rows}
                rows.update((keys[k], v) for k, v in self.memo.entries(keys).items() if keepable(v))
            if not rows or not (short or len(rows) >= hi - lo):
                continue
            with self._lock:
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
        for a, rows in took.items():
            with self._lock:
                at = self._at.get(a[0])
            if at is not None:      # an address this session asked: the rows the memo holds are not lent beside it
                held = self.memo.entries({self.key_of(at, r): r for r in rows})
                rows = {r: v for r, v in rows.items() if self.key_of(at, r) not in held}
            if rows and self.memo.lend(a, rows, sum(nbytes(None, v) for v in rows.values())):
                with self._lock:
                    self._chunks.add(a)
                    self._spans[a] = (0, 0)
                    if waiting:
                        self._waiting.add(a)

    def _address(self, e, row, cut):
        if e.kind != "frame" or e.static or e.file is not None or e.steps:
            return None
        rows = None if cut.extent.rows is None else tuple(cut.extent.rows)
        at = (e.raw_key, rows, e.reach)
        key = self._addresses.get(at)
        if key is None:
            key = self._addresses[at] = hashlib.sha1(repr(at).encode()).hexdigest()[:24] + f"-{CHUNK}rows"
            self._at[key] = at
        a = (key, row // CHUNK)
        if a not in self._spans:
            lo, hi = a[1] * CHUNK, (a[1] + 1) * CHUNK
            self._spans[a] = (lo, hi) if rows is None else (max(lo, rows[0]), min(hi, rows[1]))
        return a
