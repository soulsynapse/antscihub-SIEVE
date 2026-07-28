"""The interactive session's slice: which pools it runs, and whether they fit.

The declarations themselves — the three worker constants, the memory shares,
the sensor lists, and every function over them — are in `core/shares.py`, one
layer below everything that consumes them. What is left here is the part that
is genuinely about *this* process: an interactive session runs three pools at
once, they must leave the GUI thread a core, and on a smaller allocation they
degrade in a stated priority order.

**The split between the two files is defaults, not numbers.** Nothing below
`gui/` may *default* to the interactive split — `core.wavelet` takes every core
unless a caller caps it, which is right for a CLI run, a whole-clip pass, or a
headless parity check on a cluster node, and a module-level cap down there
would throttle exactly the runs that should saturate a node. That rule is
unchanged by the constants being reachable: `core/shares.py` is a declaration,
and applying it is the caller's act. A required `workers` argument with no
default (`detect/detector.py`) is what forces the caller to say which it is,
and it enforces at every call site where a module-level constant enforced at
none.
"""

from __future__ import annotations

from sieve.core.machine import available_cpus
from sieve.core.shares import DETECTOR_WORKERS, PLAYER_WORKERS, PREVIEW_WORKERS, WorkerSplit


def total_workers() -> int:
    """Threads the interactive session may run at once, across all three pools.

    The GUI thread is not counted: it is the thread being protected, and the
    point of the reserve is that it always has somewhere to run.
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


def resolve_worker_split(cpus: int | None = None) -> WorkerSplit:
    """The declared split, degraded to fit this machine's allocation.

    The constants in `core/shares.py` are the split on the reference class of
    machine and the *ceiling* everywhere: more cores never scale the pools up,
    because the prefetch worker optimum is a memory-bandwidth property of the
    frame buffer, not a core count — scaling up on a big machine is the exact
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
