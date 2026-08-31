"""The declaration graph: what every consumer of frames says it needs.

One contract for everything that wants data from the orchestrator — the GUI,
a tool, the series writer, the proxy builder. Each is a node that declares:
what form it wants, which rows relative to its own it needs held, and a
pressure saying how urgently it needs them.

The graph resolves those declarations into two answers the rest of the
orchestrator reads:

1. **What to hold.** Given the set of active nodes and their current
   rows, which (row, form) pairs may not be evicted? This is the
   union of every node's declared needs at its current row — the
   `residency` that `tool-experiments/tools.py` computes for steps,
   generalised to every consumer.

2. **What to fill next.** Given the pressure each node declared and the
   rows it has not yet been served, which request goes first? This is
   the priority queue the current fill and proxy do not share.

The graph is deliberately not a scheduler. It answers "what is needed" and
"what is most urgent," and the thing that calls `fill` or `decode` reads
those answers. Scheduling is policy; the graph is the facts the policy reads.

**Carried from `orchestrator-experiments/graph.py`, with one addition.**
`Need`, `Urgency`, `Envelope`, `Ref` and every derivation on `Graph` are the
ones the findings of 2026.08.30 were measured against, and are not re-argued
here — see this folder's README for what is carried and why. What is new is
that the graph *announces* a change rather than being asked about one on an
interval. V1's dispatcher slept 4 ms whenever nothing was pickable, and the
only thing that could make something pickable was a declaration arriving
here; a store of shared state that knows precisely when it changed, polled by
the one thread that cares, is the arrangement `dispatcher.py` exists
to remove.

**Listeners fire outside the lock, and that is a rule rather than a
detail.** A listener takes the core's lock and the core's `_arm` takes this
one, so firing under `self._lock` would be the two acquired in both orders.
Fired after release, there is no ordering constraint between the two locks at
all, which is the property worth having rather than an ordering worth
documenting.

What travels on an edge is an `Edge` from `contract/edges.py` in the
production code, but here it is whatever the experiment hands it — an
ndarray, a float, None. The graph does not touch payloads; it tracks
lifetimes.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable


class Urgency(IntEnum):
    """The only scheduling fact a consumer is placed to state.

    Whether a person is presently waiting on this frame is knowable from
    inside a consumer. Where it should rank against everything else in
    flight is not: that depends on what else declared the same row,
    which the declarer cannot see. Ranking was a declared field until the
    measurement in `docs/findings/` (2026.08.30, the dispatcher) — a tool
    declaring itself above a sweep bought frames by seek that the sweep was
    about to hand it sequentially, and starved the sweep doing it. This is
    ADR-0007's argument about cost classes, which are a ratio against a
    fetch the step cannot see, applied to scheduling. `Graph.pressure_queue`
    derives the rank.
    """
    DEFERRED = 0     # produce it when convenient; nobody is watching
    INTERACTIVE = 1  # a person is waiting on this frame now


@dataclass
class Need:
    """One node's declaration of what it needs right now.

    `row` is where the node considers itself — the playhead for the
    GUI, the frontier for a fill, the row being computed for a step.
    `offsets` are relative to that row, same as `Tool.offsets`.

    **A row, not a position.** This counts entries of a listing from zero;
    the contract's `position` is the source's own presentation timestamp
    (ADR-0004), and the two differ by the tick rate — at 90 kHz over 23.976
    fps, by 3753.75. Adding `offsets` to a pts is the arithmetic that reads
    every ordinary step as a jump, and it stays unavailable here by this
    field never holding one. `fetch.py` converts at the seek, which is the
    only place in this folder that needs a pts, and anything crossing into
    `sieve/` converts too.
    `form_key` names the form, same as `Form.key()`. `urgency` says only
    whether someone is waiting — the rank is the graph's to derive.
    """
    node_id: str
    row: int
    offsets: tuple[int, ...]
    form_key: str
    urgency: Urgency = Urgency.DEFERRED

    @property
    def span(self) -> int:
        """How wide a stretch this declaration covers. A consumer that
        declared a whole window is a producer for everything inside it;
        one that declared two offsets is not."""
        return max(self.offsets) - min(self.offsets) + 1

    def needed_rows(self) -> tuple[int, ...]:
        return tuple(self.row + off for off in self.offsets)

    def unserved(self, have: Callable[[int, str], bool]) -> tuple[int, ...]:
        """Needed rows `have` says are not on hand, in declared order.

        The order is the node's, not the graph's: `offsets` is a sequence,
        and a sweep that wants its window attention-first spells that by
        rotating its offsets rather than by asking the dispatcher to know
        where attention is. That keeps "what do I need" and "in what order"
        in the one declaration, which is what lets the dispatcher rank
        across nodes without knowing what any of them is.
        """
        return tuple(p for p in self.needed_rows()
                     if not have(p, self.form_key))


@dataclass
class Envelope:
    """Timing wrapper around a dispatched request. The orchestrator's clock.

    Created when a request is dispatched, closed when the result arrives.
    The graph does not time anything itself — the caller wraps its own work
    and hands the envelope back. What the graph does is accumulate them so
    the duration bars are a read of its own bookkeeping.
    """
    node_id: str
    row: int
    form_key: str
    route: str
    t_start: float = 0.0
    t_end: float = 0.0

    @property
    def ms(self) -> float:
        return (self.t_end - self.t_start) * 1000.0

    def open(self) -> "Envelope":
        self.t_start = time.perf_counter()
        return self

    def close(self) -> "Envelope":
        self.t_end = time.perf_counter()
        return self


@dataclass
class Ref:
    """A reference count on a (row, form_key) pair.

    Tracks which nodes still need this frame. When the set empties, the
    frame is eligible for eviction.
    """
    holders: set[str] = field(default_factory=set)

    @property
    def live(self) -> bool:
        return len(self.holders) > 0


class Graph:
    """The declaration graph. Nodes declare needs; the graph derives holds
    and priorities from those declarations.

    **Locked, and the lock is not an ornament.** The first version of this
    class said the caller serialised access and that scheduling was one
    thread by design. That stopped being true the moment the dispatcher
    became its own thread: the GUI declares on the Qt thread, a tool
    re-declares from its worker while it waits, and the dispatcher reads
    `pressure_queue` and appends envelopes from a third. Iterating `_needs`
    while another thread declares into it raises, and it raises rarely
    enough to look like a footage problem. Every public method holds the
    lock; each one is a dict touch, never a decode, so the lock is never
    held across anything that can block.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._needs: dict[str, Need] = {}
        self._refs: dict[tuple[int, str], Ref] = {}
        self._envelopes: list[Envelope] = []
        #: how many times each node has restated what it wants. A frame
        #: dropped and fetched again is a defect if the plan never changed
        #: in between, and only a fetch if it did — ADR-0006's split, which
        #: needs a way to tell "the declaration named this" from "somebody
        #: jumped". The generation is that way *for a node that re-declares*.
        #:
        #: **A holder that declares once cannot use it**, and that is why
        #: `release` takes `moved`. Since holding became per-activation, a
        #: consumer that supersedes itself mints a new holder rather than
        #: restating an old one, so the old holder's generation is frozen at
        #: the moment it was created and `plan_changed_since` can only ever
        #: answer "unchanged". Every re-fetch after a supersession then reads
        #: as predicted — the defect ADR-0008 targets at zero, reported by a
        #: counter structurally unable to report anything else. Measured at 10
        #: of 10 in a driven session once kf-snap made the GUI the dominant
        #: releaser.
        self._gen: dict[str, int] = {}
        #: when each node's current declaration arrived. Kept here rather
        #: than on `Need`, so `Need` stays what V1 measured; a scheduler that
        #: wants to age a declaration needs the clock and the declarer does
        #: not.
        self._declared_at: dict[str, float] = {}
        self._last_release: dict[tuple[int, str], tuple[str, int]] = {}
        #: called after any change to what is declared, never under the lock
        self._listeners: list[Callable[[], None]] = []

    def on_change(self, listener: Callable[[], None]) -> None:
        """Call *listener* whenever a declaration arrives or is released.

        What the fetch thread wakes on. The listener is told only that
        something changed, never what: deciding whether the change made
        anything pickable is the reader's, and a graph that decided it would
        be a graph that had opinions about who is reading.
        """
        with self._lock:
            self._listeners.append(listener)

    def _announce(self) -> None:
        """Fire the listeners. Never called with `self._lock` held."""
        for listener in list(self._listeners):
            listener()

    def declare(self, need: Need) -> set[tuple[int, str]]:
        """A node says what it needs now. Returns the new (row, form_key)
        pairs that were not previously held — what the caller must fetch.

        Calling `declare` again for the same `node_id` replaces the previous
        declaration and releases any rows the old one held that the new
        one does not.
        """
        with self._lock:
            old = self._needs.get(need.node_id)
            old_set: set[tuple[int, str]] = set()
            if old is not None:
                old_set = {(p, old.form_key) for p in old.needed_rows()}

            new_set = {(p, need.form_key) for p in need.needed_rows()}

            released = old_set - new_set
            for key in released:
                ref = self._refs.get(key)
                if ref is not None:
                    ref.holders.discard(need.node_id)
                    if not ref.live:
                        del self._refs[key]
                        self._last_release[key] = (
                            need.node_id, self._gen.get(need.node_id, 0),
                            False)

            added = new_set - old_set
            for key in new_set:
                ref = self._refs.setdefault(key, Ref())
                ref.holders.add(need.node_id)

            self._needs[need.node_id] = need
            self._gen[need.node_id] = self._gen.get(need.node_id, 0) + 1
            self._declared_at.setdefault(need.node_id, time.perf_counter())
        self._announce()
        return added

    def by_age(self) -> list[tuple[float, "Need"]]:
        """Every declaration with the time it arrived, oldest first.

        What a deadline needs and `pressure_queue` deliberately does not
        supply: that one ranks by urgency, subsumption and span, none of
        which knows how long anything has been waiting.
        """
        with self._lock:
            return sorted(
                ((self._declared_at.get(node_id, 0.0), need)
                 for node_id, need in self._needs.items()),
                key=lambda pair: pair[0])

    def release(self, node_id: str, moved: bool = False) -> None:
        """A node is done — release all its holds.

        `moved` says the release is itself the consumer changing its mind — a
        superseded activation, a window re-landed — rather than a consumer
        finishing with what it asked for. A re-fetch after a move is a jump
        nothing could have predicted; after a completion it is the defect.
        A holder that only ever declares once has no generation to compare, so
        this is the only thing that can tell the two apart for it.
        """
        with self._lock:
            old = self._needs.pop(node_id, None)
            self._declared_at.pop(node_id, None)
            if old is None:
                return
            for pos in old.needed_rows():
                key = (pos, old.form_key)
                ref = self._refs.get(key)
                if ref is not None:
                    ref.holders.discard(node_id)
                    if not ref.live:
                        del self._refs[key]
                        self._last_release[key] = (
                            node_id, self._gen.get(node_id, 0), moved)
        self._announce()

    def release_row(self, node_id: str, row: int, form_key: str) -> bool:
        """A node says it is done with one specific row.

        Returns True if the frame is now eligible for eviction (no holders).
        This is for non-frame nodes (series writers) that consume a frame
        and release it before moving their own row forward.

        **Announces nothing, deliberately.** A release cannot create a pick:
        `_pick` takes the first need with a row the pool does not have, and
        dropping a holder neither adds a need nor removes a frame. It can
        change *which* need is first, by unsubsuming one the releaser was
        covering — and the fetch thread re-consults after every decode
        anyway, so that reordering is seen within one frame without being
        told. Waking it per released row would put back, per row rather than
        per interval, the thing this folder removed.
        """
        with self._lock:
            key = (row, form_key)
            ref = self._refs.get(key)
            if ref is None:
                return True
            ref.holders.discard(node_id)
            if not ref.live:
                del self._refs[key]
                self._last_release[key] = (node_id,
                                           self._gen.get(node_id, 0), False)
                return True
            return False

    def still_wants(self, node_id: str, row: int, form_key: str) -> bool:
        """Does this node's *current* declaration still ask for this?

        For the dispatcher to ask after a decode it has just finished. A
        scrubbing GUI declares a row, the dispatcher preempts a
        sequential run to serve it, and by the time the seek lands the
        playhead is forty frames away — the decode was correct policy and
        wasted work, and only the count of them says how often that trade
        was bad.
        """
        with self._lock:
            need = self._needs.get(node_id)
            if need is None or need.form_key != form_key:
                return False
            return row in need.needed_rows()

    def wanter(self, row: int, form_key: str) -> str | None:
        """Who declares this row at this form, or None.

        Asked by the fetch thread once per decode and once per form it did
        not pick: a decode produces the source plane whatever form was asked
        for, so every *other* declared form of that row can be built from the
        one it already has. This is what says which of them are declared —
        building one nobody asked for would be holding on a guess, which is
        what the retention finding refused for the same reason.

        The first declarer, not all of them. The answer is used to attribute
        the put, and any node that declared it is a true answer to who it was
        produced for; the sharing counts do the rest from the reads.
        """
        with self._lock:
            for need in self._needs.values():
                if need.form_key == form_key and row in need.needed_rows():
                    return need.node_id
        return None

    def dropped_under(self,
                      key: tuple[int, str]) -> tuple[str, int, bool] | None:
        """Who last stopped needing this, at which generation, and whether the
        release was itself a change of mind. `None` if nothing ever held it."""
        with self._lock:
            return self._last_release.get(key)

    def plan_changed_since(self, node_id: str, generation: int) -> bool:
        """Has this node restated what it wants since that generation?

        The discriminator ADR-0006 asks for. A frame released and fetched
        again under an unchanged plan is a re-fetch the declaration named,
        which is a defect with an address. One fetched again after the node
        moved is a jump nothing could have predicted, and only a fetch.
        """
        with self._lock:
            return self._gen.get(node_id, 0) != generation

    def is_held(self, key: tuple[int, str]) -> bool:
        """Does any node still need this one key?

        A dict membership rather than `key in held()`, which builds a set of
        every held pair. The pool asks this on every serve to tell a victim
        hit from an ordinary one, and a serve that allocated a set the size of
        the window would be an instrument costing more than what it measures.
        """
        with self._lock:
            return key in self._refs

    def held(self) -> set[tuple[int, str]]:
        """Every (row, form_key) pair that at least one node still needs."""
        with self._lock:
            return set(self._refs.keys())

    def evictable(self, candidates: set[tuple[int, str]]) -> set[tuple[int, str]]:
        """Which of `candidates` no node needs any more."""
        with self._lock:
            return candidates - self.held()

    def pressure_queue(self) -> list[Need]:
        """Every declared need in service order — derived, never declared.

        Three keys, and only the first comes from the consumer:

        1. **Urgency.** Someone is waiting, or nobody is. A consumer knows
           this about itself and nothing else about its rank.
        2. **Not subsumed.** A need whose row is already inside a
           wider declaration yields to it. The wider one is a producer that
           will reach the row in its own order; jumping the queue for
           it buys by seek what was arriving by sequential read, and stalls
           the producer that was about to hand it over. An INTERACTIVE need
           is never subsumed — a person waiting is the case preemption is
           for.

           This is **anticipatory scheduling** (prior art: Iyer & Druschel,
           SOSP 2001) and was arrived at here the long way round. Their
           result is the stronger one and it is measured: a scheduler should
           be willing to *idle the device* rather than seek away, because the
           next request from a sequential stream is probably about to
           arrive — "deceptive idleness" being the scheduler mistaking a
           gap between requests for the absence of them. SIEVE has no
           deceptive idleness to overcome, because a declaration states a
           whole window up front and the gap the disk scheduler cannot see
           through is exactly what a declaration removes. What SIEVE has
           instead is the same trade with a worse ratio: a seek is thirty
           times a sequential read here, where on a disk it is a few.

           What that literature pairs this with, and this queue has no
           equivalent of, is a **deadline** — the guarantee that a subsumed
           need eventually runs however much INTERACTIVE traffic keeps
           arriving. Ranking for locality is precisely what starves whoever
           ranks last. `dispatcher.DEADLINE_S` is that half.
        3. **Span, widest first.** Among equals, the declaration that
           covers the most ground goes first, because it is the one whose
           order the others are riding on.
        """
        with self._lock:
            needs = list(self._needs.values())
            spans = [(n, {(p, n.form_key) for p in n.needed_rows()})
                     for n in needs]

            def subsumed(need: Need, own: set) -> bool:
                if need.urgency is Urgency.INTERACTIVE:
                    return False
                return any(other.node_id != need.node_id
                           and other.span > need.span
                           and own <= keys
                           for other, keys in spans)

            return sorted(
                needs,
                key=lambda n: (
                    -int(n.urgency),
                    int(subsumed(n, {(p, n.form_key)
                                     for p in n.needed_rows()})),
                    -n.span,
                ))

    def record(self, envelope: Envelope) -> None:
        """Record a completed timing envelope."""
        with self._lock:
            self._envelopes.append(envelope)

    def timings(self) -> list[Envelope]:
        """All recorded envelopes, in order."""
        with self._lock:
            return list(self._envelopes)

    def timings_by_node(self) -> dict[str, list[Envelope]]:
        """Envelopes grouped by node_id."""
        with self._lock:
            by_node: dict[str, list[Envelope]] = {}
            for env in self._envelopes:
                by_node.setdefault(env.node_id, []).append(env)
            return by_node

    def duration_bars(self) -> dict[str, float]:
        """Each node's fraction of total measured time.

        The numbers the pipeline cards would show as filled bars. A node
        that took 0.2 ms while the total was 100 ms reads 0.002. The
        unattributed remainder is under the key '_remainder' if the caller
        supplied wall time via `set_wall`.
        """
        with self._lock:
            by_node = self.timings_by_node()
            totals: dict[str, float] = {}
            for node_id, envs in by_node.items():
                totals[node_id] = sum(e.ms for e in envs)
            grand = sum(totals.values())
            if grand == 0:
                return {}
            return {node_id: ms / grand for node_id, ms in totals.items()}

    def clear_timings(self) -> None:
        with self._lock:
            self._envelopes.clear()
