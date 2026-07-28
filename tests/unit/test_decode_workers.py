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

from sieve.decode.prefetch import (
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

    assert inferred == min(available_cpus(), INFERRED_WORKER_CAP)
    assert 1 <= inferred <= INFERRED_WORKER_CAP
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

    assert inferred == min(available_cpus(), LUMA_WORKER_CAP)
    assert inferred <= resolve_workers()
