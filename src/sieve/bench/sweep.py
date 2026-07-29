

























from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from statistics import median

import psutil

from sieve.core.machine import cpu_classes


class AffinityUnavailableError(RuntimeError):
    pass







@dataclass(frozen=True, slots=True)
class CoreSet:


    label: str
    cpus: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.cpus:
            raise ValueError(f"core set {self.label!r} is empty")


@dataclass(frozen=True, slots=True)
class Cell:


    cores: CoreSet
    workers: int


@dataclass(frozen=True, slots=True)
class Reading:


    cell: Cell
    samples: tuple[float, ...]

    @property
    def best(self) -> float:







        return min(self.samples)

    @property
    def typical(self) -> float:

        return median(self.samples)


def class_core_sets(classes: dict[int, int] | None = None) -> tuple[CoreSet, ...]:








    published = cpu_classes() if classes is None else classes
    by_class: dict[int, list[int]] = {}
    for cpu, performance in sorted(published.items()):
        by_class.setdefault(performance, []).append(cpu)
    sets = [
        CoreSet(label=f"class{performance}x{len(cpus)}", cpus=tuple(cpus))
        for performance, cpus in sorted(by_class.items(), reverse=True)
    ]
    sets.append(CoreSet(label="unpinned", cpus=tuple(sorted(published))))
    return tuple(sets)


def sized_core_sets(source: CoreSet, sizes: Iterable[int]) -> tuple[CoreSet, ...]:






    out: list[CoreSet] = []
    for size in sorted({int(size) for size in sizes}):
        if 0 < size <= len(source.cpus):
            out.append(CoreSet(label=f"{source.label}[:{size}]", cpus=source.cpus[:size]))
    return tuple(out)


def design(cores: Sequence[CoreSet], workers: Sequence[int]) -> tuple[Cell, ...]:







    return tuple(
        Cell(cores=core_set, workers=count)
        for core_set in cores
        for count in sorted(set(workers))
        if count <= len(core_set.cpus)
    )


def sweep(
    cells: Sequence[Cell],
    objective: Callable[[Cell], float],
    *,
    repeats: int = 3,
    warmup: bool = True,
) -> tuple[Reading, ...]:























    process = psutil.Process()
    try:
        original = process.cpu_affinity()
    except (AttributeError, NotImplementedError, psutil.Error) as error:
        raise AffinityUnavailableError(f"this platform cannot pin a process: {error}") from error

    samples: dict[Cell, list[float]] = {cell: [] for cell in cells}
    try:
        if warmup:
            for cell in cells:
                _pin(process, cell)
                objective(cell)
        for _ in range(repeats):
            for cell in cells:
                _pin(process, cell)
                samples[cell].append(objective(cell))
    finally:
        process.cpu_affinity(original)

    return tuple(Reading(cell=cell, samples=tuple(taken)) for cell, taken in samples.items())


def _pin(process: psutil.Process, cell: Cell) -> None:







    try:
        process.cpu_affinity(list(cell.cores.cpus))
    except (AttributeError, NotImplementedError, psutil.Error, OSError, ValueError) as error:
        raise AffinityUnavailableError(
            f"could not pin to {cell.cores.label} ({list(cell.cores.cpus)}): {error}"
        ) from error


def curvature(readings: Sequence[Reading]) -> dict[str, float]:









    by_label: dict[str, list[float]] = {}
    for reading in readings:
        by_label.setdefault(reading.cell.cores.label, []).append(reading.best)
    return {
        label: max(values) / min(values)
        for label, values in by_label.items()
        if len(values) > 1 and min(values) > 0.0
    }
