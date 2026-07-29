








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








    first, second = _whole_allocation("a"), _whole_allocation("b")
    cells = [Cell(cores=first, workers=1), Cell(cores=second, workers=2)]
    seen: list[str] = []

    def objective(cell: Cell) -> float:
        seen.append(cell.cores.label)
        return 1.0

    sweep(cells, objective, repeats=3, warmup=False)

    assert seen == ["a", "b", "a", "b", "a", "b"]


def test_affinity_is_restored_when_the_objective_raises() -> None:






    before = psutil.Process().cpu_affinity()
    cells = [Cell(cores=_whole_allocation("only"), workers=1)]

    def objective(cell: Cell) -> float:
        raise RuntimeError("the objective failed")

    with pytest.raises(RuntimeError, match="the objective failed"):
        sweep(cells, objective, repeats=1, warmup=False)

    assert psutil.Process().cpu_affinity() == before


def test_a_mask_the_platform_refuses_is_an_error_not_an_unpinned_reading() -> None:


    absurd = CoreSet(label="nonexistent", cpus=(9999,))
    with pytest.raises(AffinityUnavailableError):
        sweep([Cell(cores=absurd, workers=1)], lambda cell: 1.0, repeats=1, warmup=False)


def test_the_design_skips_impossible_cells_rather_than_clamping_them() -> None:

    cells = design([CoreSet(label="two", cpus=(0, 1))], workers=[1, 2, 4, 8])
    assert [cell.workers for cell in cells] == [1, 2]


def test_sized_sets_are_nested_so_a_difference_is_core_count_alone() -> None:
    source = CoreSet(label="src", cpus=(4, 5, 6, 7))
    sets = sized_core_sets(source, [2, 4, 99])
    assert [core_set.cpus for core_set in sets] == [(4, 5), (4, 5, 6, 7)]


def test_class_sets_keep_unpinned_distinct_from_pinned_to_everything() -> None:

    sets = class_core_sets({0: 0, 1: 0, 2: 0, 3: 0})
    assert [core_set.label for core_set in sets] == ["class0x4", "unpinned"]
    assert sets[0].cpus == sets[1].cpus


def test_curvature_omits_a_core_set_with_one_cell_rather_than_calling_it_flat() -> None:


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
