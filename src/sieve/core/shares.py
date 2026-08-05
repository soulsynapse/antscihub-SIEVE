"""How a session divides the machine among threads and bytes: one table,
reachable from every consumer, enforcing ARCHITECTURE.md rule 5 by
arithmetic a test checks rather than by argument. Why shares are
fractions-with-floors rather than absolute numbers, and why the byte column
exists at all, is argued in `docs/ARCHITECTURE.md`'s "Dividing the machine"
and is not repeated here.

`gui/resource_probe.py` samples the session against `ledger_ceiling` and the
pools against their meters every second; `SENSED` / `WITHOUT_SENSOR` below
name which rows that reaches, the same `WITHOUT_PRODUCER` construction
`bench/budgets.py` uses for its own gap. A reading over `ledger_ceiling`
means an undeclared tenant, an under-declared share, or the reserve's
formula being wrong on this class of machine — the ceiling cannot itself
tell those apart.

**The honest gap:** `pipeline/cache.py`'s `MemoryFrameStore` is unbounded and
holds no row here (`UNBOUNDED`); it gets its bound when
`docs/todo/materialization.md` lands.

Why this table sits in `core/` while declaring a GUI session's pools, and why
`detect/detector.py` now imports `DETECTOR_WORKERS` rather than only naming
it in prose, is argued in
`docs/completed-todo/2026.07.28-machine-share-policy-is-above-its-consumers.md`
and in `gui/concurrency.py`'s own docstring.
"""

from __future__ import annotations

from dataclasses import dataclass

from sieve.core.machine import available_memory

PLAYER_WORKERS = 1

#: Decode threads the preview's reader gets, below `prefetch.py`'s colour cap
#: of four on purpose. The player already owns a decode thread on the same
#: footage and the reads-ahead hold full-resolution frames — 47.6 MB each on
#: the reference source — so a preview that made scrubbing stutter would be
#: trading an in-pipeline budget for a pre-pipeline one. Whether 2 is a
#: concession or the measured optimum depends on the graph:
#: `docs/findings/2026.07.28-the-luma-path-has-almost-nothing-left-to-thread.md`
#: (consequences).
PREVIEW_WORKERS = 2

#: Threads `scipy.fft` may use for a partial detector pass. A judgement, not a
#: measurement — nobody has profiled the three pools competing, and the day
#: someone does is the day this should change. `test_the_detector_has_the_
#: weakest_claim...` catches this exceeding `PREVIEW_WORKERS`; nothing catches
#: a value that merely contends with the other two, unmeasured.
DETECTOR_WORKERS = 2


@dataclass(frozen=True)
class WorkerSplit:
    player: int
    preview: int
    detector: int

    @property
    def total(self) -> int:
        return self.player + self.preview + self.detector


# ---- the byte column ------------------------------------------------------

#: One decoded BGR24 frame of the reference source, the unit the in-flight
#: rows below are denominated in. From the threading finding
#: (`docs/findings/2026.07.26-threading-the-reads-buys-1.6x-and-stops.md`);
#: the luma path holds 15.9 MB instead, so declaring against colour is the
#: ceiling, not the average.
REFERENCE_FRAME_BYTES = 47_600_000


#: `floor_bytes` is what the consumer was measured or reasoned at on the
#: reference class of machine — the least it can hold and still do its job.
#: `fraction` is its share of the post-reserve budget beyond that, zero for
#: consumers whose size is workload arithmetic rather than a judgement call.
@dataclass(frozen=True)
class MemoryShare:
    name: str
    floor_bytes: int
    fraction: float = 0.0


#: The scrub proxy cache (`gui/transport/proxy_cache.py`). The floor is its historical
#: 96 MB bound — `tests/gui/test_proxy_cache.py` pins the two numbers equal —
#: and the fraction is a judgement: more allocation buys more warmed grid
#: points, and one percent of a big machine is a useful cache that is still
#: nobody's OOM.
PROXY_CACHE_SHARE = MemoryShare("scrub proxy cache", floor_bytes=96 * 1024 * 1024, fraction=0.01)

#: The preview pool's reads-ahead — previously undeclared. Tracks
#: `PREVIEW_WORKERS` by construction rather than as a separate number; see
#: `decode/prefetch.py`'s `lookahead` parameter for why the factor is 2.
PREVIEW_INFLIGHT_SHARE = MemoryShare(
    "preview in-flight decodes", floor_bytes=PREVIEW_WORKERS * 2 * REFERENCE_FRAME_BYTES
)

PLAYER_INFLIGHT_SHARE = MemoryShare("player in-flight decode", floor_bytes=REFERENCE_FRAME_BYTES)

#: The render-fed playback ring (`gui/transport/render_ring.py`): the render's recent
#: source frames as display proxies, so the player can show them instead of
#: decoding the same file a second time. The floor is the bound the item
#: fixed up front — ~280 gray 1280-wide proxies, ~4.7 s at 59.94 fps. The
#: fraction is sized from measurement, not derivation:
#: `docs/findings/2026.07.28-capacity-beats-policy-in-the-render-ring.md`.
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
#: (`docs/todo/materialization.md`).
UNBOUNDED: tuple[str, ...] = ("pipeline/cache.py MemoryFrameStore",)


#: Rows of the two tables above with a producer at run time: the three pools
#: publish busy time and queue depth through their `PoolMeter`s
#: (`gui/resource_probe.py`). Names are `WorkerSplit`'s fields for pools and
#: `MemoryShare.name` for shares; `tests/unit/test_ledger_sensors.py` holds
#: this and `WITHOUT_SENSOR` to exactly the rows that exist, so a new pool or
#: share lands in one list or the other in the commit that creates it — never
#: silently in neither. Why these sit beside the rows rather than beside the
#: producers up in `gui/`:
#: `docs/completed-todo/2026.07.28-ledger-producers.md`.
SENSED: frozenset[str] = frozenset({"player", "preview", "detector"})

#: Rows with no producer of their own. The probe samples the session's RSS
#: against `ledger_ceiling`, which bounds these four rows' *sum* — no share
#: reports its own occupancy, so a tenant over its row while the total still
#: fits is invisible. This list only shrinks; moving a name to `SENSED` is
#: the deliberate edit the reconciliation test forces.
WITHOUT_SENSOR: frozenset[str] = frozenset(
    {
        "scrub proxy cache",
        "preview in-flight decodes",
        "player in-flight decode",
        "render-fed playback ring",
    }
)


#: Provisional until measured (`docs/todo/ledger-measurements.md`, H3): the
#: formula is a placeholder to argue about, not a result.
def memory_reserve(total_bytes: int) -> int:
    gib = 1024**3
    return min(4 * gib, max(2 * gib, total_bytes // 4))


def memory_budget(total_bytes: int | None = None) -> int:
    total = available_memory() if total_bytes is None else total_bytes
    return max(total - memory_reserve(total), 0)


def resolved_bytes(share: MemoryShare, total_bytes: int | None = None) -> int:
    return max(share.floor_bytes, int(share.fraction * memory_budget(total_bytes)))


def ledger_ceiling(total_bytes: int | None = None) -> int:
    total = available_memory() if total_bytes is None else total_bytes
    shares = sum(resolved_bytes(share, total) for share in MEMORY_SHARES)
    return shares + memory_reserve(total)


def fits_memory(total_bytes: int | None = None) -> bool:
    total = available_memory() if total_bytes is None else total_bytes
    floors = sum(share.floor_bytes for share in MEMORY_SHARES)
    return floors + memory_reserve(total) <= total
