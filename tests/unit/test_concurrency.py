"""Non-negotiable #5 as arithmetic, since that is the only form it can be checked in.

The rule used to be enforced by one constant with a comment justifying it
against one other consumer. That works for two and stops working at three, and
`gui/detector_worker.py` is the third. The claim under test is the one the
architecture document now makes in *Dividing the machine*: the declared split
leaves the GUI thread a core, so nobody's pool is silently bought with somebody
else's budget.
"""

from __future__ import annotations

from sieve.gui.concurrency import fits_machine, resolve_worker_split, total_workers
from sieve.mutual.shares import (
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

GIB = 1024**3


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


def test_the_split_degrades_detector_first_and_the_player_never() -> None:
    """On a small allocation the weakest claim gives way first.

    Fails if someone reorders the degradation so the preview (or the player)
    shrinks while the detector keeps its pool — which is the derivation
    outranking decode, the direction rule 5 most cares about. Also pins the
    ceiling: a big machine must NOT scale the pools up, because the four-worker
    prefetch optimum is a memory-bandwidth wall, not a core count.
    """
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
    # Below the floor split nothing shrinks further; `fits_machine` is the
    # honest report that the allocation is not what the GUI is for.
    assert resolve_worker_split(cpus=2) == four_cores
    assert not fits_machine(cpus=2)
    for cpus in range(1, 12):
        split = resolve_worker_split(cpus=cpus)
        assert split.detector <= split.preview


def test_the_declared_memory_floors_fit_a_small_real_machine() -> None:
    """The byte column's version of leaving the GUI thread a core.

    16 GB with a browser open is the smallest machine the docs promise to be
    safe on; a new share whose floor breaks this fails here rather than as
    somebody's swap storm. The tiny allocation must be *reported* unfit, not
    quietly overcommitted — and a share's resolved size never dips below the
    floor its consumer was measured at, because the ledger reports rather than
    governs.
    """
    assert fits_memory(total_bytes=16 * GIB)
    assert not fits_memory(total_bytes=1 * GIB)
    for share in MEMORY_SHARES:
        assert resolved_bytes(share, total_bytes=1 * GIB) == share.floor_bytes


def test_a_share_grows_with_the_allocation_from_its_floor() -> None:
    """Fractions of the post-reserve budget are what make one source file
    right on a laptop and a node at once; a share that stopped scaling would
    quietly reintroduce the constant this column exists to remove."""
    on_laptop = resolved_bytes(PROXY_CACHE_SHARE, total_bytes=16 * GIB)
    on_node = resolved_bytes(PROXY_CACHE_SHARE, total_bytes=256 * GIB)
    assert on_laptop >= PROXY_CACHE_SHARE.floor_bytes
    assert on_node > on_laptop


def test_the_reserve_is_bounded_at_both_ends() -> None:
    """Provisional `min(4 GB, max(2 GB, 25%))` until H3's RSS measurement
    replaces it — but the shape is load-bearing now: a reserve that scaled
    without the cap would starve the shares on exactly the big machines they
    exist to use."""
    assert memory_reserve(8 * GIB) == 2 * GIB
    assert memory_reserve(16 * GIB) == 4 * GIB
    assert memory_reserve(256 * GIB) == 4 * GIB


def test_the_preview_in_flight_share_covers_its_own_arithmetic() -> None:
    """The previously undeclared consumer: `lookahead = 2 x workers` frames in
    flight at once (`decode/prefetch.py`). If the window arithmetic or the
    worker constant moves without the declared floor moving, the ledger is
    understating the session again."""
    (preview_share,) = [s for s in MEMORY_SHARES if s.name == "preview in-flight decodes"]
    assert preview_share.floor_bytes >= PREVIEW_WORKERS * 2 * REFERENCE_FRAME_BYTES
