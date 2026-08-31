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

**Carried from `orchestrator-experiments/pool.py`, with one addition.** The
sharing counts, the byte ceiling as a backstop, and the `refetched` /
`predicted` pair are the ones ADR-0008 is counted with and are not re-argued
here.

The addition is `on_put`: a landing is announced to whoever is waiting on
that exact key, which is what lets a consumer be re-entered instead of
asking. The hook fires *after* the lock is dropped and after the payload is
visible to `has`, and both halves of that matter — a waiter registering
concurrently either sees it already there and never registers, or registers
in time to be told. Fired under the lock it would be this lock and the
dispatcher's held in one order while `_arm` holds them in the other.

**The payload is opaque, and this file has no opinion about it.** A decoded
plane, a step's field, a step's scalar: each is a key, a weight, and
something to hand back. What kinds of thing exist is `contract/edges.py`'s
`KINDS` — a closed set SIEVE alone extends, extended when a real tool presses
on it — and a store growing a second taxonomy beside that one would be
predicting what future tools need. That is the move ADR-0007 falsified for
cost classes and ADR-0009 refuses for tools generally: each accommodation is
small and justified, and their sum is a substrate shaped by the history of
requests. So there is one `put`, and it neither knows nor asks.

`_nbytes` answering 0 for anything that is not an ndarray is the same
refusal in the one place a byte ceiling cannot avoid an opinion: it weighs
what it can weigh and declines to invent the rest.

**The decode count is not here, and that is deliberate.** In V1 every put was
a decode, so `pool.decodes` and "frames decoded" were one number by accident
of there being one putter. They are not one number here. Whether a put was a
decode is known to whatever did it, so the count that compares to V1 is
`Dispatcher.served`, and this file counts `puts`.

## Pinning is correctness; replacement is policy, and V1 had only the first

This is a buffer pool, and every buffer manager has two halves (prior art: any
database buffer manager — pinned pages may not be stolen, and among unpinned
pages something ranks victims). The refcount is the pinning half and is
correct: a key some declaration still names is never evictable, which is
ADR-0006.

V1 had no replacement half at all. `_sweep_locked` dropped every unreferenced
key unconditionally, so unreferenced meant deleted, and a 16 MB frame that
cost a 300 ms seek and was about to be scrubbed back onto went on the same
terms as one that cost a 10 ms step and would never be asked for again.

Unreferenced entries are now a **victim cache** (prior art: Jouppi 1990), and
**which of them to drop is a policy this file does not choose.**
`replacement.py` holds the rules and says why the obvious one is not obviously
right: GreedyDual-Size is the textbook answer for items differing in cost and
size, and SIEVE violates its independence assumption (a frame costs a step if
its neighbour is resident and a seek if not), its online assumption (ADR-0006
says a declaration is a fetch plan, so the future is partly known), and its
random-access assumption (a scrub over a window slightly larger than the pool
is sequential flooding). So the pool takes a `Replacement`, five are written,
and an oracle among them says how much is available to win before any of the
implementable ones is argued about.

What this file supplies is the two inputs every policy needs and V1 was
throwing away: `Envelope` records what a key cost to produce and by which
route, and `_bytes` already tracks size.

**The ceiling becomes load-bearing.** `2026.08.30-derived-eviction-reproduces-
the-fixed-window` records that the byte ceiling never fired in any V1 run,
because everything unreferenced was already gone before the budget could
matter. Retaining victims is what puts the pool against its ceiling, so the
number stops being a backstop and starts being the size of the victim cache.

**No scan resistance, deliberately.** The sweep is a sequential scan over a
whole window, which under a naive policy would flush an interactive
consumer's frames — the problem ARC (Megiddo & Modha 2003) and 2Q (Johnson &
Shasha 1994) exist to solve. The refcount sidesteps it here, because anything
a consumer still declares is pinned rather than ranked. If it ever needs
solving, 2Q or CLOCK is the thing to reach for; ARC is patented, which is why
PostgreSQL and others did not use it.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np

from graph import Graph
from replacement import DropAll, Replacement


class Pool:
    """Graph-managed frame storage. Frames live until the graph says
    nobody needs them, or until the byte ceiling forces a sweep."""

    def __init__(self, graph: Graph, budget_bytes: int = 10 << 30,
                 policy: "Replacement | None" = None) -> None:
        self.graph = graph
        self.budget_bytes = budget_bytes
        #: how victims are chosen among the unpinned. `DropAll` is V1's
        #: behaviour and is the default only because it is the one every
        #: number in this folder was taken against; an experiment picks.
        self.policy = policy if policy is not None else DropAll()
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
        #: everything that landed here, whatever it was. What fraction was
        #: a decode is `Dispatcher.served`'s to say, not this file's.
        self.puts = 0
        self.shared = 0         #: serves to a node other than the producer
        self.shared_pairs: dict[str, int] = {}   #: "producer>consumer" -> n
        self.evicted = 0
        self.forced = 0         #: evictions the byte ceiling forced

        #: what was known when each evicted key was dropped: when, who
        #: last stopped needing it, and which generation of their plan that
        #: was. `stale` names work done for someone who left; `forced`
        #: names work the budget undid; this names work undone by dropping
        #: something that was still owed.
        self._dropped: dict[tuple[int, str],
                            tuple[float, str, int, bool]] = {}
        self.refetched = 0          #: decoded again after being dropped
        self.predicted = 0          #: ...under a plan that never changed
        self.refetch_gaps_ms: list[float] = []

        #: serves from a key nothing had declared — a refetch that did not
        #: happen. The direct measure of what the victim cache buys, and more
        #: immediate than watching `refetched_predicted` fail to rise.
        self.victim_hits = 0

        #: told which key landed, after the lock is dropped. `Dispatcher`
        #: installs one; nothing else needs to know.
        self._on_put: list[Any] = []

    def on_put(self, listener) -> None:
        """Call *listener* with the key of every frame that lands here."""
        self._on_put.append(listener)

    # ── read ─────────────────────────────────────────────────────────────

    def has(self, row: int, form_key: str) -> bool:
        """Is this on hand? A probe, not a serve — the dispatcher asks this
        thousands of times a second and none of it is sharing."""
        return (row, form_key) in self._frames

    def get(self, row: int, form_key: str,
            by: str | None = None) -> Any | None:
        """Serve a frame. `by` names the node reading, so a serve to
        someone other than the node whose decode produced it is counted.

        A serve is GreedyDual-Size's *hit*, and the only one: `has` is a probe
        the dispatcher performs thousands of times a second and scoring it
        would make `H` a report of the poll rate rather than of demand — the
        same reason `_counted` exists for the sharing counts.
        """
        key = (row, form_key)
        with self._lock:
            frame = self._frames.get(key)
            if frame is None:
                return None
            self.policy.hit(key)
            pinned = self.graph.is_held(key)
            if not pinned:
                #: nothing declares this and it was served anyway — under V1's
                #: policy it would have been dropped and this serve would have
                #: been a refetch. The whole of what the victim cache buys.
                self.victim_hits += 1
            if by is None:
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

    def put(self, row: int, form_key: str, payload: Any,
            by: str = "?", cost_ms: float | None = None) -> None:
        """Something lands under this key. What it is, is not asked.

        `cost_ms` is what producing it cost, and it is an input some
        replacement policies rank on. Whoever produced it has just timed it —
        the fetch thread closes an `Envelope` around every decode — so it is
        passed rather than guessed, and `None` leaves the default to the
        policy, which is the only thing placed to say what an unmeasured key
        is worth against the ones it ranks.
        """
        if not self._store((row, form_key), payload, by, cost_ms):
            return
        #: after the lock, and after `has` would answer yes. A waiter
        #: registering concurrently either sees it already there or is
        #: registered in time to be told; there is no third case.
        for listener in list(self._on_put):
            listener((row, form_key))

    def _store(self, key: tuple[int, str], frame: Any, by: str,
               cost_ms: float | None) -> bool:
        row, form_key = key
        with self._lock:
            if key in self._frames:
                return False
            dropped = self._dropped.pop(key, None)
            if dropped is not None:
                when, releaser, generation, moved = dropped
                self.refetched += 1
                self.refetch_gaps_ms.append(
                    (time.perf_counter() - when) * 1000.0)
                #: ADR-0006: a re-fetch the declaration named is a defect;
                #: one it could not have predicted is only a fetch. Two ways
                #: a consumer can have moved on — it restated its plan, which
                #: the generation shows, or the release *was* the move, which
                #: only `moved` shows. A holder that declares once and is
                #: superseded has no generation to compare, so without the
                #: second test every such re-fetch reads as the defect.
                if not (moved or self.graph.plan_changed_since(
                        releaser, generation)):
                    self.predicted += 1
            self._frames[key] = frame
            self._by[key] = by
            self.policy.admit(key, cost_ms, _nbytes(frame))
            self._bytes += _nbytes(frame)
            self.puts += 1
            if self._bytes > self.budget_bytes:
                self.forced += self._sweep_locked()
            return True

    # ── evict ────────────────────────────────────────────────────────────

    def _forget_locked(self, key: tuple[int, str], now: float) -> None:
        frame = self._frames.pop(key, None)
        if frame is not None:
            self._bytes -= _nbytes(frame)
        self._by.pop(key, None)
        self.policy.forget(key)
        who = self.graph.dropped_under(key)
        if who is not None:
            self._dropped[key] = (now, who[0], who[1], who[2])
        self.evicted += 1

    def _sweep_locked(self, to_budget: bool = True) -> int:
        """Evict unpinned keys, least valuable first, until under the ceiling.

        Pinned keys are never candidates, whatever their `H`: the refcount is
        correctness and this is policy, and policy does not get to overrule it.

        A policy is asked for one victim at a time rather than for an order.
        Every rule here except LRU depends on what is still resident — the
        contiguity one explicitly, GreedyDual-Size through its aging clock —
        so an order computed once would be stale by its second entry.
        """
        candidates = self.graph.evictable(set(self._frames.keys()))
        now = time.perf_counter()
        dropped = 0
        if not to_budget:
            for key in candidates:
                self._forget_locked(key, now)
                dropped += 1
        else:
            remaining = set(candidates)
            while remaining and self._bytes > self.budget_bytes:
                victim = self.policy.victim(remaining, self._frames.keys())
                if victim is None:
                    break
                remaining.discard(victim)
                self._forget_locked(victim, now)
                dropped += 1
        if dropped:
            live = set(self._frames)
            self._counted = {m for m in self._counted if m[0] in live}
        return dropped

    def sweep(self) -> int:
        """Evict down to the ceiling, least valuable unpinned key first.

        **Not V1's `sweep`, which dropped everything unreferenced.** A caller
        that wants that is asking for the pool to forget work it could still
        serve, which is the behaviour this class replaced; `drop_unreferenced`
        is still there for a caller that genuinely means it, and nothing in
        this folder does.
        """
        with self._lock:
            return self._sweep_locked(to_budget=True)

    def drop_unreferenced(self) -> int:
        """V1's sweep: discard every unpinned key regardless of value.

        Here so an experiment can measure against the old policy without
        reconstructing it, and for a caller that really is done — closing a
        recording, not landing a window.
        """
        with self._lock:
            return self._sweep_locked(to_budget=False)

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

    def victims(self) -> tuple[int, int]:
        """How many unpinned keys the pool is retaining, and their bytes."""
        with self._lock:
            keys = self.graph.evictable(set(self._frames.keys()))
            return len(keys), sum(_nbytes(self._frames.get(k)) for k in keys)

    def stats(self) -> dict:
        victim_count, victim_bytes = self.victims()
        return {"frames": len(self._frames),
                "bytes": self._bytes,
                "gb": round(self._bytes / (1 << 30), 3),
                "puts": self.puts,
                "shared": self.shared,
                "shared_pairs": dict(self.shared_pairs),
                "evicted": self.evicted,
                "forced_evictions": self.forced,
                "victims": victim_count,
                "victim_gb": round(victim_bytes / (1 << 30), 3),
                #: serves from a key nothing had declared: refetches that did
                #: not happen, which is what the replacement policy buys
                "victim_hits": self.victim_hits,
                "policy": self.policy.name,
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
    """`fill-140233#57` -> `fill`. An id carries an object id after a dash so
    two windows' fills are distinct holders, and a sequence after a hash since
    holding became per-activation. The sharing counter wants neither: without
    the second split, `shared_pairs` names a pair per activation and the
    "decode once, serve many" claim is reported as thousands of one-off
    sharings instead of one relationship."""
    return node_id.split("-")[0].split("#")[0]
