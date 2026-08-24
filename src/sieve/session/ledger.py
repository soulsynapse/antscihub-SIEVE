"""What the session spent, what it wasted, and what it cannot yet account for.

ADR-0008 implemented. The distinction the whole module turns on is between a
price and a mistake: **cost is reported and waste is counted.** Dense optical
flow costs what it costs and there is no version of it that is free, so the
number is information about what may be offered here rather than a problem to
be solved. A frame decoded twice, a fetch a declaration said was coming, a value
recomputed that was already stored — those are wrong on fast hardware and slow
hardware alike, they are finite, and they can be driven out.

Three things follow structurally rather than by convention, which is the point
of writing this as a module instead of a habit.

**Nothing here takes a target.** `account` closes the clocks against the
interval that actually elapsed and there is no parameter for what the interval
should have been. A ledger that could be asked "are we inside budget" would be
asked it, and every attempt this tree has made to answer that has produced work
that outlived its reason. What answers it instead is the cost class, which is
ADR-0007's to give.

**Waste and a deliberate discard are different methods.** An approximate
preview computes something it will throw away and does so because a placeholder
now beats the truth later; a coarse field drawn under load is thrown away for
the same reason. Those are choices with a stated reason, and counting them as
waste would bury the count in noise and teach everyone to ignore it. `waste` and
`chosen` cannot be reached through one another, so recording a chosen discard as
waste requires deciding to.

**The remainder is a reading, not a verdict.** Time attributed to nothing is not
by itself waste: it may be time that bought something nobody has instrumented
yet. A driven session of the tool explorer was diagnosed three times against the
instruments that existed before the remainder revealed that the largest term had
no clock on it at all. So a large `unattributed_ms` means *the instrument is
incomplete*, and the action it calls for is a clock rather than an optimisation.

**Every waste has an address.** A count with no address is a number nobody can
act on and everybody learns to ignore; the whole reason waste is worth an
instrument and cost is worth only a readout is that waste is a defect somebody
can go and find.
"""

from __future__ import annotations

import json
import threading
import time
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

# ── what counts as waste, named from ADR-0008 ────────────────────────────
#: A frame decoded twice because two consumers wanted forms one of them could
#: have served.
DOUBLE_DECODE = "double-decode"
#: A fetch that a declaration said was coming (ADR-0006). The single number
#: that makes a declaration falsifiable rather than decorative.
PREDICTED_FETCH = "predicted-fetch"
#: A computed value discarded where recording it was permitted (ADR-0005).
DISCARDED_VALUE = "discarded-value"
#: A value recomputed that was already stored under its key.
RECOMPUTED = "recomputed"
#: A render of a state that was superseded before anyone saw it.
SUPERSEDED_RENDER = "superseded-render"

WASTE_KINDS = (DOUBLE_DECODE, PREDICTED_FETCH, DISCARDED_VALUE, RECOMPUTED,
               SUPERSEDED_RENDER)

# ── work discarded on purpose: a cost, and never counted with the above ──
#: An approximate frame shown while the true one is still arriving.
PLACEHOLDER = "placeholder"
#: A field computed on coarser pixels than the answer is about.
COARSE_FIELD = "coarse-field"
#: A frame the clock passed while the machine was still drawing the last one.
UNPAINTED = "unpainted"

CHOSEN_KINDS = (PLACEHOLDER, COARSE_FIELD, UNPAINTED)

#: Steady play serves are kept one in this many. A looping session logs every
#: hit and a session that logged them all wrote tens of thousands of rows and
#: then rendered them (`docs/findings/2026.08.22-what-froze-the-felt-loop.md`).
#: What is dropped is still counted, because a decimated record that forgets
#: how much it dropped is a record that lies about the rate.
DECIMATE = 8

#: Serves kept in full before the oldest are dropped. A forgotten play session
#: should not eat the process.
EVENT_CAP = 20_000


@dataclass(frozen=True)
class Account:
    """Where an interval went, closed against what actually elapsed."""

    interval_ms: float
    clocks_ms: dict[str, float]
    attributed_ms: float
    unattributed_ms: float

    @property
    def unattributed_share(self) -> float:
        if self.interval_ms <= 0:
            return 0.0
        return self.unattributed_ms / self.interval_ms


@dataclass
class Activity:
    """One background span: what ran, when it started, when it stopped."""

    kind: str
    detail: str
    started_s: float
    ended_s: float | None = None
    note: str = ""


@dataclass
class Serve:
    """One request answered: what was wanted, which tier said so, how long."""

    at_s: float
    task: str
    tier: str
    ms: float
    row: int | None = None
    stands_for: int = 1     #: how many serves this row represents after
                            #: decimation — one unless it is a kept sample


@dataclass
class Ledger:
    """One session's record. Receives; never decides anything."""

    started_s: float = field(default_factory=time.perf_counter)
    decimate: int = DECIMATE
    cap: int = EVENT_CAP

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        self._clocks: Counter = Counter()
        self._serves: list[Serve] = []
        self._activities: list[Activity] = []
        self._waste: Counter = Counter()
        self._waste_addresses: dict[str, list[str]] = {}
        self._chosen: Counter = Counter()
        self._since_kept: Counter = Counter()
        self.serves_seen = 0
        self.serves_dropped = 0

    # ── clocks ───────────────────────────────────────────────────────────
    @contextmanager
    def clock(self, name: str):
        """Charge whatever happens in here to a named clock.

        Named rather than totalled, because a conflated clock is how a slow
        overlay reads as a slow store — which is the mistake that cost this
        tree a day and is recorded in the freeze finding.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            with self._lock:
                self._clocks[name] += (time.perf_counter() - start) * 1000

    def charge(self, name: str, ms: float) -> None:
        """Charge a clock directly, for work timed somewhere else."""
        with self._lock:
            self._clocks[name] += ms

    def account(self, interval_ms: float, *names: str) -> Account:
        """Close the named clocks against the interval that actually elapsed.

        There is no argument for what the interval should have been, and that
        absence is the decision (ADR-0008). A remainder is a reading about the
        instrument, not a verdict about the machine.
        """
        with self._lock:
            wanted = names or tuple(self._clocks)
            clocks = {name: self._clocks.get(name, 0.0) for name in wanted}
        attributed = sum(clocks.values())
        return Account(interval_ms=interval_ms, clocks_ms=clocks,
                       attributed_ms=attributed,
                       unattributed_ms=max(0.0, interval_ms - attributed))

    def reset_clocks(self) -> None:
        with self._lock:
            self._clocks.clear()

    # ── what happened ────────────────────────────────────────────────────
    def serve(self, task: str, tier: str, ms: float,
              row: int | None = None) -> None:
        """One request answered.

        Steady play is decimated and the drop is counted, so a reader can
        recover the true rate from a record that did not keep every row.
        Anything that is not steady play is kept whole: a drag, a landing and
        a miss are the events somebody is trying to explain, and they are rare
        enough to keep.
        """
        with self._lock:
            self.serves_seen += 1
            keep = True
            if task == "play" and self.decimate > 1:
                self._since_kept[tier] += 1
                if self._since_kept[tier] < self.decimate:
                    self.serves_dropped += 1
                    keep = False
                else:
                    self._since_kept[tier] = 0
            if not keep:
                return
            stands_for = self.decimate if task == "play" else 1
            self._serves.append(Serve(at_s=self.elapsed_s(), task=task,
                                      tier=tier, ms=ms, row=row,
                                      stands_for=stands_for))
            if len(self._serves) > self.cap:
                del self._serves[: len(self._serves) // 4]

    def begin(self, kind: str, detail: str = "") -> Activity:
        activity = Activity(kind=kind, detail=detail,
                            started_s=self.elapsed_s())
        with self._lock:
            self._activities.append(activity)
        return activity

    def end(self, activity: Activity, note: str = "") -> None:
        with self._lock:
            activity.ended_s = self.elapsed_s()
            activity.note = note

    # ── the two counts that must not merge ───────────────────────────────
    def waste(self, kind: str, address: str) -> None:
        """A defect with an address. Target zero.

        `address` is required and not defaulted: a count nobody can act on is
        a count everybody learns to ignore, and the reason waste is worth an
        instrument at all is that somebody can go and find it.
        """
        if kind not in WASTE_KINDS:
            raise ValueError(f"{kind!r} is not a waste kind; the kinds are "
                             f"{WASTE_KINDS}")
        if not address:
            raise ValueError("waste needs an address — what, and where")
        with self._lock:
            self._waste[kind] += 1
            self._waste_addresses.setdefault(kind, [])
            if len(self._waste_addresses[kind]) < 32:
                self._waste_addresses[kind].append(address)

    def chosen(self, kind: str) -> None:
        """Work discarded on purpose. A cost, and never waste.

        Separate from `waste` so that recording one as the other takes a
        decision rather than a slip. Counting deliberate discards as waste
        would bury the count in noise and teach everyone to ignore it.
        """
        if kind not in CHOSEN_KINDS:
            raise ValueError(f"{kind!r} is not a chosen-discard kind; the "
                             f"kinds are {CHOSEN_KINDS}")
        with self._lock:
            self._chosen[kind] += 1

    # ── reading it back ──────────────────────────────────────────────────
    def elapsed_s(self) -> float:
        return time.perf_counter() - self.started_s

    def waste_total(self) -> int:
        with self._lock:
            return sum(self._waste.values())

    def counts(self) -> dict[str, dict[str, int]]:
        with self._lock:
            return {"waste": dict(self._waste), "chosen": dict(self._chosen)}

    def serves(self) -> list[Serve]:
        with self._lock:
            return list(self._serves)

    def activities(self) -> list[Activity]:
        with self._lock:
            return list(self._activities)

    def document(self) -> dict:
        """Everything, as a plain object something else can write out."""
        with self._lock:
            return {
                "elapsed_s": self.elapsed_s(),
                "clocks_ms": dict(self._clocks),
                "serves_seen": self.serves_seen,
                "serves_dropped": self.serves_dropped,
                "decimate": self.decimate,
                "waste": dict(self._waste),
                "waste_addresses": {k: list(v) for k, v
                                    in self._waste_addresses.items()},
                "chosen": dict(self._chosen),
                "serves": [vars(s) for s in self._serves],
                "activities": [vars(a) for a in self._activities],
            }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.document(), indent=1),
                        encoding="utf-8")
        return path
