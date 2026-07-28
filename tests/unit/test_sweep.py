"""The sweep harness, judged on the two things a nested loop would get wrong.

Every cell here pins to the *whole* current allocation, so the mask the tests
set is the mask that was already in force. `bench/sweep.py` says a sweep does
not belong beside other work because affinity is unscoped global state, and a
test suite that pinned itself to four cores to prove it could would be the
thing that module refuses.
"""

from __future__ import annotations

import psutil
import pytest

from sieve.bench.sweep import (
    AffinityUnavailableError,
    Cell,
    CoreSet,
    Reading,
    class_core_sets,
    curvature,
    design,
    sized_core_sets,
    sweep,
)
from sieve.core.machine import available_cpu_ids


def _whole_allocation(label: str) -> CoreSet:
    return CoreSet(label=label, cpus=available_cpu_ids())


def test_samples_are_interleaved_across_cells_not_blocked() -> None:
    """The claim the module exists for: no cell is measured all at once.

    Blocked execution is what made the reference machine's readings a function
    of running order, so a harness that ran cell A's three samples and then
    cell B's would hand the whole drift to B. Asserted as the call *sequence*
    rather than as timings, because a timing assertion here would be measuring
    the machine to test the loop.
    """
    first, second = _whole_allocation("a"), _whole_allocation("b")
    cells = [Cell(cores=first, workers=1), Cell(cores=second, workers=2)]
    seen: list[str] = []

    def objective(cell: Cell) -> float:
        seen.append(cell.cores.label)
        return 1.0

    sweep(cells, objective, repeats=3, warmup=False)

    assert seen == ["a", "b", "a", "b", "a", "b"]


def test_affinity_is_restored_when_the_objective_raises() -> None:
    """A sweep that dies mid-cell must not leave the process pinned.

    The failure this guards is silent and outlives the run: every later
    measurement in the same process would be taken on the last cell's cores
    while reporting nothing about it.
    """
    before = psutil.Process().cpu_affinity()
    cells = [Cell(cores=_whole_allocation("only"), workers=1)]

    def objective(cell: Cell) -> float:
        raise RuntimeError("the objective failed")

    with pytest.raises(RuntimeError, match="the objective failed"):
        sweep(cells, objective, repeats=1, warmup=False)

    assert psutil.Process().cpu_affinity() == before


def test_a_mask_the_platform_refuses_is_an_error_not_an_unpinned_reading() -> None:
    """Refusing beats sampling — an unpinned sample under a pinned label is
    the machine axis quietly becoming noise."""
    absurd = CoreSet(label="nonexistent", cpus=(9999,))
    with pytest.raises(AffinityUnavailableError):
        sweep([Cell(cores=absurd, workers=1)], lambda cell: 1.0, repeats=1, warmup=False)


def test_the_design_skips_impossible_cells_rather_than_clamping_them() -> None:
    """A clamped cell would report the 2-worker reading under the label 8."""
    cells = design([CoreSet(label="two", cpus=(0, 1))], workers=[1, 2, 4, 8])
    assert [cell.workers for cell in cells] == [1, 2]


def test_sized_sets_are_nested_so_a_difference_is_core_count_alone() -> None:
    source = CoreSet(label="src", cpus=(4, 5, 6, 7))
    sets = sized_core_sets(source, [2, 4, 99])
    assert [core_set.cpus for core_set in sets] == [(4, 5), (4, 5, 6, 7)]


def test_class_sets_keep_unpinned_distinct_from_pinned_to_everything() -> None:
    """Same mask, different treatment: only one of them permits migration."""
    sets = class_core_sets({0: 0, 1: 0, 2: 0, 3: 0})
    assert [core_set.label for core_set in sets] == ["class0x4", "unpinned"]
    assert sets[0].cpus == sets[1].cpus


def test_curvature_omits_a_core_set_with_one_cell_rather_than_calling_it_flat() -> None:
    """One point has no spread, and 1.0 would read as a measured flatness —
    which is the exact finding that would close the controller question."""
    one = CoreSet(label="one", cpus=(0,))
    many = CoreSet(label="many", cpus=(0, 1))
    readings = [
        Reading(cell=Cell(cores=one, workers=1), samples=(10.0,)),
        Reading(cell=Cell(cores=many, workers=1), samples=(10.0,)),
        Reading(cell=Cell(cores=many, workers=2), samples=(5.0,)),
    ]
    spread = curvature(readings)
    assert "one" not in spread
    assert spread["many"] == pytest.approx(2.0)
