"""What a bare walk keeps of a frame node's rows between processes: a Graph handed a Keeper asks it
on a memo miss and tells it each row it made; the rows go to result_store over its Folder a
chunk at a time. Only rows that are no image (ndim < 2 arrays, tables, scalars) of frame nodes that
are not static, served or stepped are kept. No failure of the folder reaches the caller.
"""
import hashlib
import os
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np

from .budget import gb
from .recent import app_folder
from .result_store import Address, Folder, Store
from .wire import nbytes

CHUNK = 256         # rows a chunk holds; in every address's name
ANSWERS = 8         # chunks read back held at once: a walk in order reads one a node, and a tool near its row the one before
FOLDER_ENV, BUDGET_ENV = "SIEVE_RESULTS", "SIEVE_RESULTS_GB"
BUDGET = 20 << 30


def player_print():
    """A digest of sieve_player's own .py files as they lie on disk now."""
    h = hashlib.sha1()
    root = Path(__file__).parent
    for path in sorted(root.rglob("*.py")):
        h.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return h.hexdigest()[:16]


def keepable(row):
    """Whether a row made is of a shape the keeper keeps: no image, no reference to another store's array."""
    return (isinstance(row, np.ndarray) and row.ndim < 2) or isinstance(row, (np.generic, int, float))


class Keeper:
    """The rows of walks over `root`, `budget` bytes of disk; the user's folder and budget, by
    FOLDER_ENV and BUDGET_ENV over the defaults, with neither handed. An address is the row's raw
    key, which holds the footage as decoder.footage_print samples it and the code of every tool
    above as discover imported it, the cut's rows, the node's reach, and this player's code and libraries: footage changed
    only where that print does not sample it is taken for the one before. A walk asks and tells it
    on its one thread and calls `close()` when it ends, which puts every chunk it filled any of."""

    def __init__(self, root=None, budget=None):
        self.answers, self.pending = OrderedDict(), {}
        self.asked, self.changed, self.done, self.addresses = set(), set(), set(), {}
        try:
            root = root or os.environ.get(FOLDER_ENV) or os.path.join(app_folder(), "results")
            self.store = Store(Folder(root, f"bare{os.getpid()}"), 0, budget or gb(BUDGET_ENV, os.environ) or BUDGET)
            self.libraries = (player_print(), np.__version__, cv2.__version__)
        except Exception:
            self.store = None

    def ask(self, e, row, cut):
        """`e`'s row `row` in `cut` as a walk before kept it, read-only, or None."""
        a = self._address(e, row, cut)
        if a is None:
            return None
        if a not in self.asked:
            self.asked.add(a)
            self.answers[a] = held = self._read(a)
            if len(held) >= CHUNK:
                self.done.add(a)
            elif held:
                self.pending[a] = dict(held)
            while len(self.answers) > ANSWERS:
                self.answers.popitem(last=False)
        return self.answers.get(a, {}).get(row)

    def made(self, e, row, cut, value):
        """`value` is what `e` made at `row` in `cut`, as the memo holds it."""
        a = self._address(e, row, cut)
        if a is None or a in self.done or not keepable(value):
            return
        rows = self.pending.setdefault(a, {})
        rows[row] = value
        self.changed.add(a)
        if len(rows) >= CHUNK:
            self._put(a)

    def close(self):
        for a in list(self.pending):
            self._put(a)

    def _address(self, e, row, cut):
        if self.store is None or e.kind != "frame" or e.static or e.file is not None or e.steps:
            return None
        at = (e.raw_key, None if cut.extent.rows is None else tuple(cut.extent.rows), e.reach)
        if at not in self.addresses:
            self.addresses[at] = hashlib.sha1(repr((at, self.libraries)).encode()).hexdigest()[:24] + f"-{CHUNK}rows"
        return Address(self.addresses[at], row // CHUNK)

    def _read(self, a):
        try:
            got = self.store.get(a)
            if not isinstance(got, dict) or not all(isinstance(r, int) and r // CHUNK == a.chunk and keepable(v) for r, v in got.items()):
                return {}
            for v in got.values():
                if isinstance(v, np.ndarray):
                    v.setflags(write=False)
            return got
        except Exception:
            return {}

    def _put(self, a):
        rows = self.pending.pop(a)
        self.done.add(a)
        if a not in self.changed:
            return
        try:
            if self.store.disk.size(a.name) is not None:
                self.store.drop(a, "disk")
            self.store.put(a, rows, sum(nbytes(None, v) for v in rows.values()), keep=True)
        except Exception:
            pass
