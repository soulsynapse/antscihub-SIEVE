"""Which unpinned key to evict — five rules, so the choice is measured.

The pool is a buffer pool and every buffer manager has two halves (prior art:
any database buffer manager). Pinning is correctness: a key some declaration
still names may not be stolen, which is ADR-0006 and is not negotiable.
**Replacement is policy**, ranks victims among the unpinned, and V1 had none —
`_sweep_locked` dropped every unreferenced key unconditionally, so unreferenced
meant deleted and a 16 MB frame that cost a 300 ms seek went on the same terms
as one that cost a 10 ms step.

This file exists because the obvious replacement for that was asserted and not
proved. GreedyDual-Size is the textbook answer for items differing in cost and
size, and SIEVE violates three of its assumptions:

- **Costs are not independent.** GD-Size ranks each item alone, but a frame
  costs a step if its neighbour is resident and a seek if it is not
  (`2026.08.21-uncut-seek-costs-a-gop-not-a-frame`). The value of keeping row
  *n* depends on whether row *n−1* was kept, which the algorithm cannot say.
- **The future is not unknown.** GD-Size is an *online* algorithm and its
  justification is competitiveness against an adversary. SIEVE is built on
  declarations, and ADR-0006 says a declaration is a fetch plan — reaching for
  an online policy in a system that is told what will be asked for is using
  the wrong half of the literature.
- **Access is not random.** A person scrubbing a window slightly larger than
  the cache is the textbook worst case for recency ranking — sequential
  flooding — and the answers there are ring buffers for scans (prior art:
  PostgreSQL's `BAS_BULKREAD`) or partitioning, not better ranking.

So all five are implemented and measured against each other, including an
oracle that cannot be built in production and exists to say how much is
available to win at all. If the oracle buys little, every policy question
below it is moot.

    drop-all     V1: discard every unpinned key. The baseline being replaced.
    lru          recency. What anyone reaches for first, and what the cost
                 argument above says should be beaten.
    gdsize       `H = L + cost/size` (prior art: Cao & Irani 1997). Evict the
                 minimum, raise the aging clock to what was evicted, so age
                 falls out of the arithmetic without timestamps.
    contiguous   evict the most isolated key first, so what survives is runs
                 rather than confetti. Aimed at the dependent-cost objection:
                 a scattered half-window must be seeked through, and the wall
                 is a sequential term plus a third of a second per seek
                 (`2026.08.30-the-pressure-dispatcher-preempts-into-seeks`).
    belady       evict whatever is needed furthest in the future (prior art:
                 Belady 1966). Unimplementable — it is told the script — and
                 it is the ceiling every other row is read against.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable


class Replacement:
    """The interface a pool asks. Lower rank is evicted first.

    Every hook is a dict touch and is called under the pool's lock, which is
    the same rule the pool states about itself: nothing here may block, and
    nothing here may decode.
    """

    name = "none"

    def admit(self, key: tuple[int, str], cost_ms: float, nbytes: int) -> None:
        """A key has landed."""

    def hit(self, key: tuple[int, str]) -> None:
        """A key was served. Not called for a `has` probe, which the
        dispatcher performs thousands of times a second and which is not
        evidence of demand."""

    def forget(self, key: tuple[int, str]) -> None:
        """A key has gone, however it went."""

    def victim(self, candidates: set[tuple[int, str]],
               resident: Iterable[tuple[int, str]]) -> tuple[int, str] | None:
        """The next key to evict from *candidates*, all of them unpinned.

        `resident` is everything the pool holds, pinned included, because a
        policy reasoning about neighbours needs to know a neighbour is there
        whether or not it may itself be evicted.
        """
        raise NotImplementedError


class DropAll(Replacement):
    """V1: every unpinned key goes, whatever it cost and whatever is next.

    Here as the thing being replaced, so the comparison does not have to
    reconstruct it.
    """

    name = "drop-all"

    def victim(self, candidates, resident):
        return next(iter(candidates), None)


class LRU(Replacement):
    """Least recently used, by a serial counter rather than a clock.

    The default anyone reaches for. It ranks by recency alone, so it cannot
    tell a key that cost a seek from one that cost a step — which is the
    whole of the argument for something else, and the reason this arm is run
    rather than assumed to lose.
    """

    name = "lru"

    def __init__(self) -> None:
        self._seq: dict[tuple[int, str], int] = {}
        self._n = 0

    def _bump(self, key):
        self._n += 1
        self._seq[key] = self._n

    def admit(self, key, cost_ms, nbytes):
        self._bump(key)

    def hit(self, key):
        self._bump(key)

    def forget(self, key):
        self._seq.pop(key, None)

    def victim(self, candidates, resident):
        return min(candidates, key=lambda k: self._seq.get(k, 0),
                   default=None)


class GreedyDualSize(Replacement):
    """`H = L + cost/size`; evict the minimum and raise `L` to it.

    Prior art: Cao & Irani 1997. The size floor of one byte keeps a scalar —
    whose `nbytes` is 0 — from dividing by zero, and incidentally gives it an
    `H` nothing undercuts, which is the right answer for a payload that costs
    something to make and nothing to keep.

    `L` is monotone: a key admitted later starts above everything already
    discarded, which is how the policy ages without storing a time.
    """

    name = "gdsize"

    def __init__(self, default_cost_ms: float = 1.0) -> None:
        self.default_cost_ms = default_cost_ms
        self._cost: dict[tuple[int, str], float] = {}
        self._size: dict[tuple[int, str], int] = {}
        self._h: dict[tuple[int, str], float] = {}
        self.l = 0.0

    def _refresh(self, key):
        size = max(1, self._size.get(key, 1))
        self._h[key] = self.l + self._cost.get(key,
                                               self.default_cost_ms) / size

    def admit(self, key, cost_ms, nbytes):
        self._cost[key] = (self.default_cost_ms if cost_ms is None
                           else float(cost_ms))
        self._size[key] = nbytes
        self._refresh(key)

    def hit(self, key):
        if key in self._h:
            self._refresh(key)

    def forget(self, key):
        self._cost.pop(key, None)
        self._size.pop(key, None)
        self._h.pop(key, None)

    def victim(self, candidates, resident):
        chosen = min(candidates, key=lambda k: self._h.get(k, 0.0),
                     default=None)
        if chosen is not None:
            self.l = max(self.l, self._h.get(chosen, self.l))
        return chosen


class Contiguous(Replacement):
    """Evict the most isolated key, so what survives is runs.

    The answer to GD-Size's independence assumption rather than a better
    ranking under it. A retained set that is scattered has to be seeked
    through, and a seek is worth about thirty sequential reads here, so a
    policy that keeps half a window as confetti can hand the sweep a worse
    job than keeping none of it. Ranking by how many neighbours are resident
    concentrates whatever survives.

    Ties break toward the older key, which makes this LRU within a run and
    keeps it from thrashing the two ends of a long one.
    """

    name = "contiguous"

    def __init__(self, radius: int = 1) -> None:
        self.radius = radius
        self._seq: dict[tuple[int, str], int] = {}
        self._n = 0

    def admit(self, key, cost_ms, nbytes):
        self._n += 1
        self._seq[key] = self._n

    def forget(self, key):
        self._seq.pop(key, None)

    def victim(self, candidates, resident):
        live = set(resident)

        def neighbours(key):
            row, form_key = key
            return sum(1 for d in range(-self.radius, self.radius + 1)
                       if d != 0 and (row + d, form_key) in live)

        return min(candidates,
                   key=lambda k: (neighbours(k), self._seq.get(k, 0)),
                   default=None)


class Belady(Replacement):
    """Evict whatever is needed furthest in the future. The ceiling.

    Prior art: Belady 1966, MIN. Cannot be built — it is handed the script the
    experiment is about to run — and it is here to answer the question that
    comes before every policy question: how much is there to win at all. A
    result where the best implementable policy sits near this one says the
    remaining gap is not worth chasing; one where they are far apart says the
    ranking is where the loss is.

    `next_use` returns the step index at which a key is next demanded, or
    None for never.
    """

    name = "belady"

    def __init__(self,
                 next_use: Callable[[tuple[int, str]], int | None]) -> None:
        self.next_use = next_use

    def victim(self, candidates, resident):
        def when(key):
            nxt = self.next_use(key)
            return float("inf") if nxt is None else float(nxt)

        return max(candidates, key=when, default=None)


#: by name, for an experiment that takes its arms off the command line
POLICIES: dict[str, Any] = {
    DropAll.name: DropAll,
    LRU.name: LRU,
    GreedyDualSize.name: GreedyDualSize,
    Contiguous.name: Contiguous,
    Belady.name: Belady,
}
