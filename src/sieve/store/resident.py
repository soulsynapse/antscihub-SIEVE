"""Frames held in memory, keyed by the picture as well as the instant.

A map and a lock, and every operation under that lock is a dict touch — never a
decode, never a file. That is the property that lets the GUI thread ask this
question, and it is why nothing here takes a route.

**Keyed by form, not by row.** The explorers key on the row alone over a global
crop rect, which forces two things that both go away here: a display frame and a
crop frame cannot be resident at once, so the hunt tier re-decodes a proxy
segment on every request; and changing the crop means wiping the store, because
the frames in it are the wrong picture and nothing can say so. Keyed by
`(form.key(), row)` neither follows. Two pictures of one instant coexist, and a
crop change simply misses.

That is not a claim that a crop change becomes cheap — it does not.
`02-form-derivation` measured that deriving pays only where decode is expensive,
which is where the dominating form is too heavy to hold much of, so the window
tier still refills rather than deriving its way out of a new crop. What form
keying buys is that the refill is a *miss* rather than an erasure, and that the
old picture is still there if the crop comes back.

**Eviction consults residency and nothing else is protected.** ADR-0006 already
decides this: what may not be evicted is what the active declarations need over
the run of positions about to be served, and everything outside that set is this
store's to drop. That is also why there are no per-form budgets. One budget
across every form, with a protected set, is the arrangement in which a window
fill cannot quietly evict the whole scrub cache — the failure the decode
explorer's cache docstring exists to make feelable.

**Nearest is a bisect, not a scan.** The explorers answer "what have you got
near this row" with a `min()` over every key, under the lock, on the GUI thread,
per non-exact request. Coverage is kept sorted per form here, so the same
question is a binary search, and "what is covered in this span" stops being a
full pass.
"""

from __future__ import annotations

import threading
from bisect import bisect_left, insort
from collections import OrderedDict

import numpy as np

#: How far from the wanted row a held frame may be and still be offered as a
#: stand-in. A stand-in is shown and never recorded, so this is a judgement
#: about what reads as the same moment rather than a measurement; a caller that
#: wants a tighter answer passes its own.
NEAR_RADIUS = 12


class ResidentStore:
    """Budget-capped frames in memory, keyed by `(form key, row)`."""

    def __init__(self, budget_bytes: int):
        self.budget_bytes = budget_bytes
        self.used_bytes = 0
        self._frames: OrderedDict[tuple[str, int], np.ndarray] = OrderedDict()
        #: rows per form, kept sorted so `nearest` is a search
        self._rows: dict[str, list[int]] = {}
        self.lock = threading.RLock()
        self.evicted = 0

    # ── reading ──────────────────────────────────────────────────────────
    def get(self, form_key: str, row: int) -> np.ndarray | None:
        with self.lock:
            key = (form_key, row)
            frame = self._frames.get(key)
            if frame is not None:
                self._frames.move_to_end(key)
            return frame

    def nearest(self, form_key: str, row: int,
                radius: int = NEAR_RADIUS) -> tuple[int, np.ndarray] | None:
        """The held row closest to `row` within `radius`, and its frame.

        Returned as a pair so the caller knows *which* frame it got. A
        stand-in that does not say how far off it is cannot be shown honestly
        and cannot be refused when it is too far.
        """
        with self.lock:
            rows = self._rows.get(form_key)
            if not rows:
                return None
            index = bisect_left(rows, row)
            best = None
            for candidate in (index - 1, index):
                if 0 <= candidate < len(rows):
                    offset = abs(rows[candidate] - row)
                    if offset <= radius and (best is None or offset < best[0]):
                        best = (offset, rows[candidate])
            if best is None:
                return None
            landed = best[1]
            frame = self._frames.get((form_key, landed))
            return None if frame is None else (landed, frame)

    def covered(self, form_key: str, start: int, end: int) -> list[int]:
        """Which rows of `[start, end)` are held, in order."""
        with self.lock:
            rows = self._rows.get(form_key)
            if not rows:
                return []
            left = bisect_left(rows, start)
            right = bisect_left(rows, end)
            return rows[left:right]

    def coverage(self, form_key: str, start: int, end: int) -> float:
        span = max(0, end - start)
        if not span:
            return 0.0
        return len(self.covered(form_key, start, end)) / span

    # ── writing ──────────────────────────────────────────────────────────
    def put(self, form_key: str, row: int, frame: np.ndarray,
            protected: set[tuple[str, int]] | None = None) -> None:
        """Hold a frame, evicting unprotected ones until it fits.

        `protected` is a residency set — what the active declarations need over
        the horizon about to be served. It is passed in rather than remembered
        because it is a pure function of the position being served (ADR-0006),
        and a store that cached it would be answering with a set that was true
        when the playhead was somewhere else.
        """
        with self.lock:
            key = (form_key, row)
            if key in self._frames:
                self.used_bytes -= self._frames[key].nbytes
            else:
                insort(self._rows.setdefault(form_key, []), row)
            self._frames[key] = frame
            self._frames.move_to_end(key)
            self.used_bytes += frame.nbytes
            self._evict(protected or set())

    def _evict(self, protected: set[tuple[str, int]]) -> None:
        """Drop least-recent unprotected frames until inside the budget.

        A store whose protected set alone exceeds the budget stays over it
        rather than dropping something it was told not to. That is the honest
        failure: the declaration is larger than the machine, which is a fact
        about which execution strategies remain (ADR-0006) and not something
        this store may resolve by disobeying.
        """
        if self.used_bytes <= self.budget_bytes:
            return
        for key in list(self._frames):
            if self.used_bytes <= self.budget_bytes:
                return
            if key in protected:
                continue
            frame = self._frames.pop(key)
            self.used_bytes -= frame.nbytes
            self.evicted += 1
            rows = self._rows.get(key[0])
            if rows:
                index = bisect_left(rows, key[1])
                if index < len(rows) and rows[index] == key[1]:
                    rows.pop(index)
                if not rows:
                    self._rows.pop(key[0], None)

    def drop_form(self, form_key: str) -> int:
        """Forget one picture entirely. Returns how many frames went.

        Here for a caller that knows a form will not be wanted again — not for
        a crop change, which is a miss and does not need anyone's help.
        """
        with self.lock:
            keys = [k for k in self._frames if k[0] == form_key]
            for key in keys:
                self.used_bytes -= self._frames.pop(key).nbytes
            self._rows.pop(form_key, None)
            return len(keys)

    def set_budget(self, budget_bytes: int,
                   protected: set[tuple[str, int]] | None = None) -> None:
        with self.lock:
            self.budget_bytes = budget_bytes
            self._evict(protected or set())

    # ── what a check or a readout asks ───────────────────────────────────
    def forms(self) -> set[str]:
        with self.lock:
            return set(self._rows)

    def __len__(self) -> int:
        with self.lock:
            return len(self._frames)
