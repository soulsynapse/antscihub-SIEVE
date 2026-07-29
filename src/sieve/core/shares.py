from __future__ import annotations

from dataclasses import dataclass

from sieve.core.machine import available_memory


PLAYER_WORKERS = 1


PREVIEW_WORKERS = 2


DETECTOR_WORKERS = 2


@dataclass(frozen=True)
class WorkerSplit:
    player: int
    preview: int
    detector: int

    @property
    def total(self) -> int:
        return self.player + self.preview + self.detector


REFERENCE_FRAME_BYTES = 47_600_000


@dataclass(frozen=True)
class MemoryShare:
    name: str
    floor_bytes: int
    fraction: float = 0.0


PROXY_CACHE_SHARE = MemoryShare(
    "scrub proxy cache", floor_bytes=96 * 1024 * 1024, fraction=0.01
)


PREVIEW_INFLIGHT_SHARE = MemoryShare(
    "preview in-flight decodes", floor_bytes=PREVIEW_WORKERS * 2 * REFERENCE_FRAME_BYTES
)


PLAYER_INFLIGHT_SHARE = MemoryShare(
    "player in-flight decode", floor_bytes=REFERENCE_FRAME_BYTES
)


RENDER_RING_SHARE = MemoryShare(
    "render-fed playback ring", floor_bytes=256 * 1024 * 1024, fraction=0.01
)


MEMORY_SHARES: tuple[MemoryShare, ...] = (
    PROXY_CACHE_SHARE,
    PREVIEW_INFLIGHT_SHARE,
    PLAYER_INFLIGHT_SHARE,
    RENDER_RING_SHARE,
)


UNBOUNDED: tuple[str, ...] = ("pipeline/cache.py MemoryFrameStore",)


SENSED: frozenset[str] = frozenset({"player", "preview", "detector"})


WITHOUT_SENSOR: frozenset[str] = frozenset(
    {
        "scrub proxy cache",
        "preview in-flight decodes",
        "player in-flight decode",
        "render-fed playback ring",
    }
)


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
