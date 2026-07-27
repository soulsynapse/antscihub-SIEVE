"""Non-negotiable #5 as arithmetic, since that is the only form it can be checked in.

The rule used to be enforced by one constant with a comment justifying it
against one other consumer. That works for two and stops working at three, and
`gui/detector_worker.py` is the third. The claim under test is the one the
architecture document now makes in *Dividing the machine*: the declared split
leaves the GUI thread a core, so nobody's pool is silently bought with somebody
else's budget.
"""

from __future__ import annotations

from sieve.gui.concurrency import (
    DETECTOR_WORKERS,
    PLAYER_WORKERS,
    PREVIEW_WORKERS,
    fits_machine,
    total_workers,
)


def test_the_declared_split_leaves_the_gui_thread_a_core() -> None:
    """The whole of non-negotiable #5's mechanism.

    Fails when someone adds a fourth consumer or raises a constant without
    accounting for the others — which is exactly the change that would
    otherwise land as a scrub that stutters on somebody else's machine three
    commits later, with nothing pointing at the cause.
    """
    assert total_workers() == PLAYER_WORKERS + PREVIEW_WORKERS + DETECTOR_WORKERS
    assert fits_machine(cpus=8), "the split must fit an ordinary 8-core workstation"


def test_a_machine_too_small_for_the_split_is_reported_rather_than_assumed() -> None:
    """`fits_machine` answers about the *allocation*, not the machine.

    A single-core job step cannot host the interactive session, and the honest
    answer is False rather than a silently oversubscribed pool. This is the
    case a container or a pinned SLURM step actually produces, which is why
    the count comes from `available_cpus` rather than `os.cpu_count`.
    """
    assert not fits_machine(cpus=1)
    assert not fits_machine(cpus=total_workers())
    assert fits_machine(cpus=total_workers() + 1)


def test_the_detector_has_the_weakest_claim_on_the_machine() -> None:
    """The derivation may never outrank decode.

    A graph that fills more coarsely is a degraded nicety; a stuttering scrub
    is a broken budget with a 100 ms ceiling and a user watching it. If this
    ever inverts, #5 has been traded away in the direction the rule most cares
    about.
    """
    assert DETECTOR_WORKERS <= PREVIEW_WORKERS
