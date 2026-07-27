"""How the interactive session divides the machine. One place, so it adds up.

ARCHITECTURE.md non-negotiable #5 says no consumer improves its latency at
another's expense. Until now that was enforced by one constant with a comment
(`PREVIEW_WORKERS = 2`, justified against the player's decode thread) and by
nobody having added a third consumer. `gui/detector_worker.py` is the third,
and it runs `scipy.fft`, whose default is *every core* — so the rule stopped
being self-enforcing the moment a derivation thread existed.

**The rule is arithmetic, so it is declared and tested rather than argued.**
Three consumers run concurrently during ordinary tuning:

* the player's decode thread — one, `gui/decode_worker.py`, pre-pipeline, and
  the one holding the 100 ms scrub budget;
* the preview's decode pool — `PREVIEW_WORKERS`, in-pipeline, feeding renders;
* the detector's FFT — `DETECTOR_WORKERS`, in-pipeline, deriving the graphs.

`total_workers` sums them and `tests/unit/test_concurrency.py` asserts the sum
leaves the machine a core. That is the whole mechanism: a fourth consumer, or a
raised constant, fails a test rather than quietly degrading a budget somebody
measures three commits later.

**`core/` holds none of this.** `core.wavelet` defaults to every core and is
right to: a CLI run, a whole-clip pass, and a headless parity check on a
cluster node have nobody to leave room for, and a module-level cap in `core/`
would throttle exactly the runs that should saturate a node. Policy about
sharing a machine belongs to the process that is sharing one, which is this
one. `available_cpus` is imported rather than re-derived for the reason
`resolve_workers` documents at length — two callers disagreeing about how much
of a node they have is a slow job nobody can explain.
"""

from __future__ import annotations

from sieve.decode.prefetch import available_cpus

#: Decode threads the player owns. One, and not a tunable: the scrub budget is
#: met by degrading to the coarse grid (`gui/scrub_policy.py`), not by decoding
#: on more threads, so this is a fact about the design rather than a knob.
PLAYER_WORKERS = 1

#: Decode threads the preview's reader gets, below `prefetch.py`'s inferred cap
#: of four on purpose. The player already owns a decode thread on the same
#: footage and the reads-ahead hold full-resolution frames — 47.6 MB each on
#: the reference source — so a preview that made scrubbing stutter would be
#: trading an in-pipeline budget for a pre-pipeline one.
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
