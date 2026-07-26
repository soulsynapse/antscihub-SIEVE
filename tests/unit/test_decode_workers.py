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

from sieve.decode.prefetch import INFERRED_WORKER_CAP, available_cpus, resolve_workers


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
