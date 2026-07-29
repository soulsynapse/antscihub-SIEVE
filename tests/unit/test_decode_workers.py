













from __future__ import annotations

from sieve.decode.prefetch import (
    INFERRED_WORKER_CAP,
    LUMA_WORKER_CAP,
    available_cpus,
    resolve_workers,
)


def test_an_explicit_request_is_never_capped_or_second_guessed() -> None:







    assert resolve_workers(32) == 32
    assert resolve_workers(1) == 1



    assert resolve_workers(0) == 1
    assert resolve_workers(-4) == 1



    assert resolve_workers(32, luma=True) == 32
    assert resolve_workers(0, luma=True) == 1


def test_an_inferred_count_is_this_process_s_allocation_and_is_capped() -> None:











    inferred = resolve_workers()

    assert inferred == min(available_cpus(), INFERRED_WORKER_CAP)
    assert 1 <= inferred <= INFERRED_WORKER_CAP
    assert available_cpus() >= 1


def test_the_luma_path_infers_its_own_lower_cap() -> None:











    assert LUMA_WORKER_CAP < INFERRED_WORKER_CAP

    inferred = resolve_workers(luma=True)

    assert inferred == min(available_cpus(), LUMA_WORKER_CAP)
    assert inferred <= resolve_workers()
