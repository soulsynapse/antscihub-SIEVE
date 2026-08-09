"""How many decode threads a run gets, and why the answer is not `cpu_count()`.

Two claims, no video, and both fail silently if broken: a run that ignores an
explicit count runs slowly on a machine the user configured correctly, and one
that reads the machine's core count instead of this process's allocation
oversubscribes a shared node. Neither produces a wrong frame, so nothing else in
this suite would notice.

An earlier version of this file had four tests, three of which pinned the
precedence between `SLURM_CPUS_PER_TASK` and a `SIEVE_DECODE_WORKERS` override.
Both variables are gone — see `resolve_workers` — and so are those tests, which
is the honest outcome: they existed to check rules that existed to be checked.
"""

from __future__ import annotations

import pytest

from sieve.decode.prefetch import (
    CORES_PER_WORKER,
    INFERRED_WORKER_CAP,
    LUMA_WORKER_CAP,
    available_cpus,
    resolve_workers,
)


def test_an_explicit_request_is_never_capped_or_second_guessed() -> None:
    """A caller that names a number gets it, above the inferred ceiling.

    `INFERRED_WORKER_CAP` bounds a guess about a machine this code cannot see; a
    cluster node passing 32 can see it. Fails if the cap is applied to the request
    rather than to the inference, which would hold an HPC run to a handful of
    threads on a 96-core node with nothing in the output to say so.
    """
    assert resolve_workers(32) == 32
    assert resolve_workers(1) == 1
    # Zero and negatives are a caller's arithmetic gone wrong — `workers - 1`, a
    # flag that defaulted to 0 — and one worker is the sequential path, so they
    # resolve there rather than raising or starting no threads at all.
    assert resolve_workers(0) == 1
    assert resolve_workers(-4) == 1
    # The luma cap is lower, which makes it the tempting one to apply to a
    # request. It is still an inference bound: a node that measured its own
    # curve outranks either constant.
    assert resolve_workers(32, luma=True) == 32
    assert resolve_workers(0, luma=True) == 1


def test_an_inferred_count_is_this_process_s_allocation_and_is_capped() -> None:
    """What the machine allows, bounded, and never zero.

    `available_cpus` asks `sched_getaffinity` where it exists, because
    `os.cpu_count()` reports the machine and is the wrong answer inside a cgroup,
    a container, or a job step pinned to part of a node — all three ordinary on
    the hardware this runs on, and the middle one is how CI runs.

    The cap is a memory bound rather than a CPU one: the window holds `lookahead`
    full-resolution frames and one is 47.6 MB on the reference source, so a guess
    of 32 workers would reserve gigabytes on a laptop that merely has the cores.
    """
    inferred = resolve_workers()

    assert 1 <= inferred <= min(available_cpus(), INFERRED_WORKER_CAP)
    assert available_cpus() >= 1


def test_the_luma_path_infers_its_own_lower_cap() -> None:
    """Two, not four, and the difference is a measurement rather than caution.

    Declining the colour convert removes most of what threading was overlapping,
    so the curve peaks at two workers (6.41 ms/frame against a sequential 8.49)
    and four is 7.88 — a 21% regression, not a wash. Inferring the colour cap
    here makes every luma run slower with nothing in the output to say so, which
    is precisely the failure the ledger item called out as invisible.

    Pinned as an inequality plus the identity, so the test says *which way* the
    two caps must differ rather than merely restating both constants.
    """
    assert LUMA_WORKER_CAP < INFERRED_WORKER_CAP

    inferred = resolve_workers(luma=True)

    assert 1 <= inferred <= min(available_cpus(), LUMA_WORKER_CAP)
    assert inferred <= resolve_workers()


def test_a_small_allocation_is_not_handed_more_workers_than_it_can_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every worker gets `CORES_PER_WORKER` cores, or it is not started.

    A cap bounds the guess from above and has no term that can see the bottom of
    the range, so the smaller the allocation the worse it guesses — the opposite
    of the direction a ceiling is meant to fail in. The sweep measured what that
    costs on the luma path: two workers on four CPUs is 16.12 ms/frame against a
    sequential 12.08, and on two CPUs 31.08 against 20.37. A clamped count is not
    leaving throughput on the table there, it is slower than not threading at
    all, and a cluster job step is where it lands.

    The sizes are patched rather than taken from the machine on purpose. The
    whole defect is at allocation sizes no developer machine has, and a resolver
    whose only exercised input is `available_cpus()` on the runner is the reason
    it survived the port.
    """

    def resolved(cpus: int, *, luma: bool) -> int:
        monkeypatch.setattr("sieve.decode.prefetch.available_cpus", lambda: cpus)
        return resolve_workers(luma=luma)

    # The sizes the 2026-08-09 sweep read the luma path at. Two and four are
    # where the cap was a regression against sequential; sixteen and thirty-two
    # are where it was exactly right, and must not move.
    assert resolved(2, luma=True) == 1
    assert resolved(4, luma=True) == 1
    assert resolved(16, luma=True) == LUMA_WORKER_CAP
    assert resolved(32, luma=True) == LUMA_WORKER_CAP

    # The colour path's core-count axis was never swept, so what is claimed here
    # is only that the same floor applies and that neither whole-allocation
    # reading moves.
    assert resolved(16, luma=False) == INFERRED_WORKER_CAP
    assert resolved(32, luma=False) == INFERRED_WORKER_CAP

    for cpus in range(1, 65):
        for luma in (True, False):
            workers = resolved(cpus, luma=luma)
            assert workers >= 1
            assert workers <= cpus
            if workers > 1:
                assert cpus // workers >= CORES_PER_WORKER

    # The floor is a bound on the inference and not on the request, for the same
    # reason the caps are not: a two-CPU allocation is what a caller who passed
    # `--workers 8` is most likely to be lying about deliberately.
    monkeypatch.setattr("sieve.decode.prefetch.available_cpus", lambda: 2)
    assert resolve_workers(8, luma=True) == 8
