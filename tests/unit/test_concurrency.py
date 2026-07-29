









from __future__ import annotations

from sieve.core.shares import (
    DETECTOR_WORKERS,
    MEMORY_SHARES,
    PLAYER_WORKERS,
    PREVIEW_WORKERS,
    PROXY_CACHE_SHARE,
    REFERENCE_FRAME_BYTES,
    fits_memory,
    memory_reserve,
    resolved_bytes,
)
from sieve.gui.concurrency import fits_machine, resolve_worker_split, total_workers

GIB = 1024**3


def test_the_declared_split_leaves_the_gui_thread_a_core() -> None:







    assert total_workers() == PLAYER_WORKERS + PREVIEW_WORKERS + DETECTOR_WORKERS
    assert fits_machine(cpus=8), "the split must fit an ordinary 8-core workstation"


def test_a_machine_too_small_for_the_split_is_reported_rather_than_assumed() -> None:







    assert not fits_machine(cpus=1)
    assert not fits_machine(cpus=total_workers())
    assert fits_machine(cpus=total_workers() + 1)


def test_the_detector_has_the_weakest_claim_on_the_machine() -> None:







    assert DETECTOR_WORKERS <= PREVIEW_WORKERS


def test_the_split_degrades_detector_first_and_the_player_never() -> None:








    reference = resolve_worker_split(cpus=8)
    assert (reference.player, reference.preview, reference.detector) == (
        PLAYER_WORKERS,
        PREVIEW_WORKERS,
        DETECTOR_WORKERS,
    )
    assert resolve_worker_split(cpus=64) == reference

    five_cores = resolve_worker_split(cpus=5)
    assert (five_cores.player, five_cores.preview, five_cores.detector) == (1, 2, 1)
    four_cores = resolve_worker_split(cpus=4)
    assert (four_cores.player, four_cores.preview, four_cores.detector) == (1, 1, 1)


    assert resolve_worker_split(cpus=2) == four_cores
    assert not fits_machine(cpus=2)
    for cpus in range(1, 12):
        split = resolve_worker_split(cpus=cpus)
        assert split.detector <= split.preview


def test_the_declared_memory_floors_fit_a_small_real_machine() -> None:









    assert fits_memory(total_bytes=16 * GIB)
    assert not fits_memory(total_bytes=1 * GIB)
    for share in MEMORY_SHARES:
        assert resolved_bytes(share, total_bytes=1 * GIB) == share.floor_bytes


def test_a_share_grows_with_the_allocation_from_its_floor() -> None:



    on_laptop = resolved_bytes(PROXY_CACHE_SHARE, total_bytes=16 * GIB)
    on_node = resolved_bytes(PROXY_CACHE_SHARE, total_bytes=256 * GIB)
    assert on_laptop >= PROXY_CACHE_SHARE.floor_bytes
    assert on_node > on_laptop


def test_the_reserve_is_bounded_at_both_ends() -> None:




    assert memory_reserve(8 * GIB) == 2 * GIB
    assert memory_reserve(16 * GIB) == 4 * GIB
    assert memory_reserve(256 * GIB) == 4 * GIB


def test_the_preview_in_flight_share_covers_its_own_arithmetic() -> None:




    (preview_share,) = [s for s in MEMORY_SHARES if s.name == "preview in-flight decodes"]
    assert preview_share.floor_bytes >= PREVIEW_WORKERS * 2 * REFERENCE_FRAME_BYTES
