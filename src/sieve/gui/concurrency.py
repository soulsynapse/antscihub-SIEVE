




















from __future__ import annotations

from sieve.core.machine import available_cpus
from sieve.core.shares import DETECTOR_WORKERS, PLAYER_WORKERS, PREVIEW_WORKERS, WorkerSplit


def total_workers() -> int:





    return PLAYER_WORKERS + PREVIEW_WORKERS + DETECTOR_WORKERS


def fits_machine(cpus: int | None = None) -> bool:








    return total_workers() <= max((available_cpus() if cpus is None else cpus) - 1, 0)


def resolve_worker_split(cpus: int | None = None) -> WorkerSplit:














    budget = max((available_cpus() if cpus is None else cpus) - 1, 0)
    player, preview, detector = PLAYER_WORKERS, PREVIEW_WORKERS, DETECTOR_WORKERS
    while player + preview + detector > budget and detector > 1:
        detector -= 1
    while player + preview + detector > budget and preview > 1:
        preview -= 1
    return WorkerSplit(player=player, preview=preview, detector=detector)
