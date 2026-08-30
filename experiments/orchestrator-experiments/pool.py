"""The graph-managed frame pool: hold, reserve, release, evict, and say who shared.

What the `Store` in the earlier explorers was — a budget-capped LRU of
decoded frames — except the budget is now the graph's declarations rather
than a fixed count. A frame is held because at least one node declared it;
it is evicted when the last declaration releases it.

The pool does not decode. It holds what something else decoded, and drops
it when the graph says nobody needs it any more. The caller that decodes is
the dispatcher; the callers that release are the nodes that consumed; the
pool is the thing between them whose job is to know whether a frame that
was decoded for one consumer can also serve another — and to *count* when
it does, because "decode once, serve many" is the claim the whole graph is
built on and an uncounted claim is an assertion.

**The budget is bytes, not frames.** A frame-count cap was honest while a
frame was a 1 MB crop. At full frame it is ~16 MB, and the same count is
two orders of magnitude of difference in what the cap means. The cap here
is a byte ceiling; how many frames that buys is a consequence of the form,
which is the direction the dependency should run.

**The lock is for the dispatcher.** Every operation under it is a dict
touch and never a decode. A lock a decode runs inside is the dispatcher
stalling whoever is drawing, which is the freeze the session explorer
exists to avoid and the orchestrator must not re-introduce.

**Keyed by (row, form_key).** Two consumers at different forms need
different arrays of one instant, and a pool keyed by row alone would
think one satisfied the other — the same lesson `store.py` already learned.

The row is an ordinal against the caller's listing and not the contract's
`position`, which is a pts. `store.py` is keyed by the same shape in the
other coordinate, so the two keys are not interchangeable however alike
they read — see `graph.Need`.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np

from graph import Graph


class Pool:
    """Graph-managed frame storage. Frames live until the graph says
    nobody needs them, or until the byte ceiling forces a sweep."""

    def __init__(self, graph: Graph, budget_bytes: int = 10 << 30) -> None:
        self.graph = graph
        self.budget_bytes = budget_bytes
        self._frames: dict[tuple[int, str], Any] = {}
        #: which node's decode put each frame here — the other half of a
        #: shared serve, and the only reason the pool knows what to count
        self._by: dict[tuple[int, str], str] = {}
        self._bytes = 0
        self._lock = threading.Lock()

        #: a (key, consumer) is counted shared once, not once per poll. A
        #: tool waiting on a frame reads the same key every 5 ms, and a
        #: counter that scored each of those would report the poll rate.
        self._counted: set[tuple[tuple[int, str], str]] = set()
        self.decodes = 0        #: frames put by a decode
        self.shared = 0         #: serves to a node other than the producer
        self.shared_pairs: dict[str, int] = {}   #: "producer>consumer" -> n
        self.evicted = 0
        self.forced = 0         #: evictions the byte ceiling forced

        #: what was known when each evicted key was dropped: when, who
        #: last stopped needing it, and which generation of their plan that
        #: was. `stale` names work done for someone who left; `forced`
        #: names work the budget undid; this names work undone by dropping
        #: something that was still owed.
        self._dropped: dict[tuple[int, str], tuple[float, str, int]] = {}
        self.refetched = 0          #: decoded again after being dropped
        self.predicted = 0          #: ...under a plan that never changed
        self.refetch_gaps_ms: list[float] = []

    # ── read ─────────────────────────────────────────────────────────────

    def has(self, row: int, form_key: str) -> bool:
        """Is this on hand? A probe, not a serve — the dispatcher asks this
        thousands of times a second and none of it is sharing."""
        return (row, form_key) in self._frames

    def get(self, row: int, form_key: str,
            by: str | None = None) -> Any | None:
        """Serve a frame. `by` names the node reading, so a serve to
        someone other than the node whose decode produced it is counted."""
        key = (row, form_key)
        with self._lock:
            frame = self._frames.get(key)
            if frame is None or by is None:
                return frame
            producer = self._by.get(key)
            if producer is not None and producer != by:
                mark = (key, by)
                if mark not in self._counted:
                    self._counted.add(mark)
                    self.shared += 1
                    pair = f"{_short(producer)}>{_short(by)}"
                    self.shared_pairs[pair] = self.shared_pairs.get(pair, 0) + 1
            return frame

    # ── write ────────────────────────────────────────────────────────────

    def put(self, row: int, form_key: str, frame: Any,
            by: str = "?") -> None:
        key = (row, form_key)
        with self._lock:
            if key in self._frames:
                return
            dropped = self._dropped.pop(key, None)
            if dropped is not None:
                when, releaser, generation = dropped
                self.refetched += 1
                self.refetch_gaps_ms.append(
                    (time.perf_counter() - when) * 1000.0)
                #: ADR-0006: a re-fetch the declaration named is a defect;
                #: one it could not have predicted is only a fetch. The
                #: plan not having changed since the drop is what "named
                #: it" means — the consumer still wants what it wanted,
                #: and the frame went anyway.
                if not self.graph.plan_changed_since(releaser, generation):
                    self.predicted += 1
            self._frames[key] = frame
            self._by[key] = by
            self._bytes += _nbytes(frame)
            self.decodes += 1
            if self._bytes > self.budget_bytes:
                self.forced += self._sweep_locked()

    # ── evict ────────────────────────────────────────────────────────────

    def _sweep_locked(self) -> int:
        evictable = self.graph.evictable(set(self._frames.keys()))
        now = time.perf_counter()
        for key in evictable:
            frame = self._frames.pop(key, None)
            if frame is not None:
                self._bytes -= _nbytes(frame)
            self._by.pop(key, None)
            who = self.graph.dropped_under(key)
            if who is not None:
                self._dropped[key] = (now, who[0], who[1])
        self._counted = {m for m in self._counted if m[0] not in evictable}
        self.evicted += len(evictable)
        return len(evictable)

    def sweep(self) -> int:
        """Evict everything the graph says is free. Returns count evicted."""
        with self._lock:
            return self._sweep_locked()

    # ── query ────────────────────────────────────────────────────────────

    def nearest(self, row: int, form_key: str,
                radius: int) -> tuple[int, Any] | None:
        """The closest held frame within `radius`, at this form."""
        with self._lock:
            best_dist = radius + 1
            best_pos = None
            best_frame = None
            for (p, fk), frame in self._frames.items():
                if fk != form_key:
                    continue
                d = abs(p - row)
                if d < best_dist:
                    best_dist = d
                    best_pos = p
                    best_frame = frame
            if best_pos is not None:
                return best_pos, best_frame
        return None

    def covered(self, start: int, end: int, form_key: str) -> list[int]:
        """Rows held in [start, end) at this form, sorted."""
        with self._lock:
            return sorted(p for (p, fk) in self._frames
                          if fk == form_key and start <= p < end)

    @property
    def nbytes(self) -> int:
        return self._bytes

    def stats(self) -> dict:
        return {"frames": len(self._frames),
                "bytes": self._bytes,
                "gb": round(self._bytes / (1 << 30), 3),
                "decodes": self.decodes,
                "shared": self.shared,
                "shared_pairs": dict(self.shared_pairs),
                "evicted": self.evicted,
                "forced_evictions": self.forced,
                "refetched": self.refetched,
                #: the number ADR-0006 calls the one that makes the
                #: arrangement falsifiable. Target zero. `refetched` alone
                #: is not an accusation — coming back to a window is a
                #: fetch, not a mistake.
                "refetched_predicted": self.predicted,
                "refetch_gap_ms_p50": (
                    round(sorted(self.refetch_gaps_ms)[
                        len(self.refetch_gaps_ms) // 2], 1)
                    if self.refetch_gaps_ms else None)}

    def __len__(self) -> int:
        return len(self._frames)

    def wipe(self) -> None:
        with self._lock:
            self._frames.clear()
            self._by.clear()
            self._counted.clear()
            self._dropped.clear()
            self._bytes = 0


def _nbytes(frame: Any) -> int:
    return int(frame.nbytes) if isinstance(frame, np.ndarray) else 0


def _short(node_id: str) -> str:
    """`fill-140233...` -> `fill`. Node ids carry an object id so two
    windows' fills are distinct holders; the counter wants the role."""
    return node_id.split("-")[0]
