"""How the interactive session divides the machine. One place, so it adds up.

ARCHITECTURE.md rule 5 says no consumer improves its latency at another's
expense, and the enforcement is arithmetic rather than argument: every path
that can take more than one core — **or a bounded slab of memory** — declares
its share here, and a test checks the sum against what the machine actually
allocates. A fourth consumer, or a raised constant, fails a test rather than
quietly degrading a budget somebody measures three commits later.

The thread column came first (`PREVIEW_WORKERS = 2` justified in a comment
stopped being a rule the moment `gui/detector_worker.py` made a third
consumer). The byte column exists because the bandwidth finding showed that
counting threads misses resources that actually bind, and memory is the next
one: the retention policy wants a byte budget, cache eviction wants a bound,
and render-fed playback wants a ring size, and each would otherwise be a
number in a different file, wrong on most machines, and unaccountable in sum.

**Shares are fractions of the post-reserve budget with declared floors**, not
absolute numbers — that is what makes this file right on a 16 GB laptop and a
256 GB node at once. The floors are the values the current code was measured
at on the reference class of machine; the fractions are how a share grows
when the allocation does. A consumer whose floor cannot be met is *reported*
(`fits_memory`), exactly as `fits_machine` reports a one-core allocation: the
ledger is never a runtime governor — but it is no longer only a sum a test
checks. `gui/resource_probe.py` samples the session against `ledger_ceiling`
and the pools against their meters every second, so a machine where these
declarations are wrong now produces evidence instead of a feeling. What has a
producer and what still does not is stated by `SENSED` / `WITHOUT_SENSOR`
below, `bench/budgets.py`'s `WITHOUT_PRODUCER` construction applied to this
file's own tables.

**The honest gap:** `pipeline/cache.py`'s `MemoryFrameStore` is unbounded and
holds no row here — see `UNBOUNDED`. It gets its bound when
`docs/todo/cache-eviction.md` lands; naming the gap is what keeps the sum
below from reading as complete while it is not (rule 6).

**`core/` holds none of this.** `core.wavelet` defaults to every core and is
right to: a CLI run, a whole-clip pass, and a headless parity check on a
cluster node have nobody to leave room for, and a module-level cap in `core/`
would throttle exactly the runs that should saturate a node. Policy about
sharing a machine belongs to the process that is sharing one, which is this
one. The *readings* — `available_cpus`, `available_memory` — live in
`core/machine.py` and are imported rather than re-derived, for the reason
`resolve_workers` documents at length: two callers disagreeing about how much
of a node they have is a slow job nobody can explain, and an OOM kill when
the resource is bytes.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.core.machine import available_cpus, available_memory

#: Decode threads the player owns. One, and not a tunable: the scrub budget is
#: met by degrading to the coarse grid (`gui/scrub_policy.py`), not by decoding
#: on more threads, so this is a fact about the design rather than a knob.
PLAYER_WORKERS = 1

#: Decode threads the preview's reader gets, below `prefetch.py`'s colour cap
#: of four on purpose. The player already owns a decode thread on the same
#: footage and the reads-ahead hold full-resolution frames — 47.6 MB each on
#: the reference source — so a preview that made scrubbing stutter would be
#: trading an in-pipeline budget for a pre-pipeline one.
#:
#: That was a concession when it was written and is no longer one on the path
#: the preview actually takes: the preview opens luma whenever no node needs
#: chroma (`gui/preview_runner.py`), and two is the *measured optimum* there —
#: `prefetch.py`'s `LUMA_WORKER_CAP`, from
#: `docs/findings/2026.07.28-the-luma-path-has-almost-nothing-left-to-thread.md`.
#: On a colour graph it remains the concession it always was.
PREVIEW_WORKERS = 2

#: Threads `scipy.fft` may use for a partial detector pass. The smallest number
#: that is still a pool: the derivation is the newest consumer and the one with
#: the weakest claim, because a graph that fills a little more coarsely is a
#: degraded nicety where a stuttering scrub is a broken budget.
#:
#: A judgement, not a measurement — nobody has profiled the three pools
#: competing, and the day someone does is the day this should change. What is
#: measured is only that the sum below leaves the machine room.
DETECTOR_WORKERS = 2


def total_workers() -> int:
    """Threads the interactive session may run at once, across all three pools.

    The GUI thread is not counted: it is the thread being protected, and the
    point of the reserve below is that it always has somewhere to run.
    """
    return PLAYER_WORKERS + PREVIEW_WORKERS + DETECTOR_WORKERS


def fits_machine(cpus: int | None = None) -> bool:
    """Whether the declared split leaves this machine a core for the GUI thread.

    `None` asks `available_cpus`, which reports the process's affinity or cgroup
    allocation rather than the machine's core count — the right question inside
    a container or a job step, and the ordinary case on the hardware this runs
    on. A single-core allocation cannot satisfy this and is not meant to: the
    interactive GUI is not what a one-core job step is for.
    """
    return total_workers() <= max((available_cpus() if cpus is None else cpus) - 1, 0)


@dataclass(frozen=True)
class WorkerSplit:
    """The three pools as resolved for one machine, not as declared."""

    player: int
    preview: int
    detector: int

    @property
    def total(self) -> int:
        return self.player + self.preview + self.detector


def resolve_worker_split(cpus: int | None = None) -> WorkerSplit:
    """The declared split, degraded to fit this machine's allocation.

    The constants above are the split on the reference class of machine and
    the *ceiling* everywhere: more cores never scale the pools up, because the
    prefetch worker optimum is a memory-bandwidth property of the frame
    buffer, not a core count — scaling up on a big machine is the exact
    mistake the 8- and 12-worker measurements already made.

    On smaller allocations the split degrades in priority order: detector
    first (its own docstring calls it the weakest claim), then preview. Never
    below one thread each — below that, `fits_machine` is already False and
    the allocation is not one the GUI is for, so the floor split is returned
    rather than a zero a pool cannot run on.
    """
    budget = max((available_cpus() if cpus is None else cpus) - 1, 0)
    player, preview, detector = PLAYER_WORKERS, PREVIEW_WORKERS, DETECTOR_WORKERS
    while player + preview + detector > budget and detector > 1:
        detector -= 1
    while player + preview + detector > budget and preview > 1:
        preview -= 1
    return WorkerSplit(player=player, preview=preview, detector=detector)


# ---- the byte column ------------------------------------------------------

#: One decoded BGR24 frame of the reference source, the unit the in-flight
#: rows below are denominated in. From the threading finding
#: (`docs/findings/2026.07.26-threading-the-reads-buys-1.6x-and-stops.md`);
#: the luma path holds 15.9 MB instead, so declaring against colour is the
#: ceiling, not the average.
REFERENCE_FRAME_BYTES = 47_600_000


@dataclass(frozen=True)
class MemoryShare:
    """One consumer's declared claim on the session's byte budget.

    `floor_bytes` is the size the consumer was measured or reasoned at on the
    reference class of machine — the least it can hold and still do its job.
    `fraction` is its share of the post-reserve budget beyond that, zero for
    consumers whose size is workload arithmetic (an in-flight buffer is
    `workers x lookahead x frame`, however much memory the machine has).
    """

    name: str
    floor_bytes: int
    fraction: float = 0.0


#: The scrub proxy cache (`gui/proxy_cache.py`). The floor is its historical
#: 96 MB bound — `tests/gui/test_proxy_cache.py` pins the two numbers equal —
#: and the fraction is a judgement: more allocation buys more warmed grid
#: points, and one percent of a big machine is a useful cache that is still
#: nobody's OOM.
PROXY_CACHE_SHARE = MemoryShare("scrub proxy cache", floor_bytes=96 * 1024 * 1024, fraction=0.01)

#: The preview pool's reads-ahead — previously undeclared and real. At most
#: `lookahead = 2 x PREVIEW_WORKERS` full-resolution frames exist at once
#: (`decode/prefetch.py`'s window arithmetic), so the floor *is* that product
#: and moves with the constant above rather than drifting from it.
PREVIEW_INFLIGHT_SHARE = MemoryShare(
    "preview in-flight decodes", floor_bytes=PREVIEW_WORKERS * 2 * REFERENCE_FRAME_BYTES
)

#: The player's decode thread holds one frame between decode and paint.
#: Declared for completeness, so the table is the whole session.
PLAYER_INFLIGHT_SHARE = MemoryShare("player in-flight decode", floor_bytes=REFERENCE_FRAME_BYTES)

#: The render-fed playback ring (`gui/render_ring.py`): the render's recent
#: source frames as display proxies, so the player can show them instead of
#: decoding the same file a second time. The floor is the bound the item
#: fixed up front — ~280 gray 1280-wide proxies, ~4.7 s at 59.94 fps, enough
#: that a playhead a few seconds behind the frontier never misses.
#:
#: The fraction is the retention finding's one portable consequence
#: (`docs/findings/2026.07.28-capacity-beats-policy-in-the-render-ring.md`):
#: capacity beat eviction policy 60:1 at the operating point, so the ring
#: deserves to grow with the allocation. One percent lands the 68 GB machine
#: measured there on ~700 proxies, which is the ~720 its working set saturated
#: at — sized to reach a large machine's own knee, not to hardcode 720. The
#: floor is unchanged so a small machine pays nothing for that: below ~26 GB
#: the fraction is under the floor and the floor is what resolves, which is
#: also the case the finding explicitly could not settle.
RENDER_RING_SHARE = MemoryShare(
    "render-fed playback ring", floor_bytes=256 * 1024 * 1024, fraction=0.01
)

#: Every bounded slab the interactive session holds. A new consumer adds a row
#: here in the commit that creates it, or it is the undeclared tenant H4's
#: instrumentation exists to catch.
MEMORY_SHARES: tuple[MemoryShare, ...] = (
    PROXY_CACHE_SHARE,
    PREVIEW_INFLIGHT_SHARE,
    PLAYER_INFLIGHT_SHARE,
    RENDER_RING_SHARE,
)

#: Consumers that hold real memory and no row above — the ledger's honest gap,
#: the same construction as `bench/budgets.py`'s `WITHOUT_PRODUCER`. This list
#: only shrinks: `MemoryFrameStore` gets its bound when cache eviction lands
#: (`docs/todo/cache-eviction.md`).
UNBOUNDED: tuple[str, ...] = ("pipeline/cache.py MemoryFrameStore",)


#: Rows of the two tables above whose declared numbers something at run time
#: now produces evidence about: the three pools publish busy time and queue
#: depth through their `PoolMeter`s, read by `gui/resource_probe.py`. Names are
#: `WorkerSplit`'s fields for pools and `MemoryShare.name` for shares;
#: `tests/unit/test_ledger_sensors.py` holds the two sets to exactly the rows
#: that exist, so a new pool or share lands in one list or the other in the
#: commit that creates it — never silently in neither.
SENSED: frozenset[str] = frozenset({"player", "preview", "detector"})

#: Rows with no producer of their own — the honest gap, `WITHOUT_PRODUCER`'s
#: construction. The memory shares are here as a body: the probe samples the
#: session's RSS against `ledger_ceiling`, which bounds their *sum*, but no
#: share reports its own occupancy, so a tenant over its row while the total
#: still fits is invisible. This list only shrinks; moving a name to `SENSED`
#: is the deliberate edit the reconciliation test forces.
WITHOUT_SENSOR: frozenset[str] = frozenset(
    {
        "scrub proxy cache",
        "preview in-flight decodes",
        "player in-flight decode",
        "render-fed playback ring",
    }
)


def memory_reserve(total_bytes: int) -> int:
    """Bytes the ledger refuses to allocate: Python, Qt, the decoder's own
    buffers — everything the table above cannot see.

    Provisional until measured — `min(4 GB, max(2 GB, 25%))` is a formula to
    argue about, and the measurement that replaces it is the session's RSS
    floor on the reference workstation (H3 in the ledger item; queued in
    `docs/todo/ledger-measurements.md`).
    """
    gib = 1024**3
    return min(4 * gib, max(2 * gib, total_bytes // 4))


def memory_budget(total_bytes: int | None = None) -> int:
    """What the declared shares divide: the allocation minus the reserve.

    `None` asks `available_memory`, which reports the allocation and never the
    machine — the cgroup limit inside a container or a job step, the
    scheduler's declaration, physical RAM only on a desktop.
    """
    total = available_memory() if total_bytes is None else total_bytes
    return max(total - memory_reserve(total), 0)


def resolved_bytes(share: MemoryShare, total_bytes: int | None = None) -> int:
    """The share's size on this machine: its fraction of the budget, floored.

    The floor holds even when the budget cannot honour it — the ledger is not
    a governor, and a cache sized to zero would be a second failure mode. What
    reports the overcommit is `fits_memory`, the same division of labour as
    the thread column's `fits_machine`.
    """
    return max(share.floor_bytes, int(share.fraction * memory_budget(total_bytes)))


def ledger_ceiling(total_bytes: int | None = None) -> int:
    """What a session's measured RSS is judged against: every declared share
    as resolved for this machine, plus the reserve.

    The standing comparison `docs/todo/ledger-measurements.md` wanted run once
    on the reference workstation, computed instead on whatever machine the
    session is on — which is the point: the reserve's formula models total RAM
    while the session-floor finding showed memory tracks the working window,
    and per-machine readings against this ceiling are how that mismatch stops
    being one finding and starts being every session's evidence.

    A reading *over* this ceiling means an undeclared tenant, an
    under-declared share, or the reserve's formula being wrong on this class
    of machine — the three things `UNBOUNDED` and the reserve's own docstring
    can only warn about.
    """
    total = available_memory() if total_bytes is None else total_bytes
    shares = sum(resolved_bytes(share, total) for share in MEMORY_SHARES)
    return shares + memory_reserve(total)


def fits_memory(total_bytes: int | None = None) -> bool:
    """Whether the declared floors plus the reserve fit this allocation.

    False means a consumer's floor cannot be met and the session would
    overcommit — the honest report, per rule 6, rather than a quiet swap
    storm. As with `fits_machine`, a tiny allocation is not what the
    interactive GUI is for.
    """
    total = available_memory() if total_bytes is None else total_bytes
    floors = sum(share.floor_bytes for share in MEMORY_SHARES)
    return floors + memory_reserve(total) <= total
