"""Sweep a cost over core sets and worker counts, so a constant can be judged.

`bench/budgets.py` holds ceilings and `tests/bench/` asks whether one commit
met them. Neither can answer whether worker allocation
is actually about, which is not "what is the optimum here" but **how sharp is
it** — a flat optimum makes a controller a failure mode with no upside, and a
sharp one makes a per-machine constant wrong everywhere it was not measured.
That is a property of a response surface, and a point measurement cannot state
it however carefully the point is taken.

**Affinity is the machine axis.** `core/machine.py` reports which CPUs a
process may use and what class each one is; restricting to a subset synthesizes
core configurations this hardware does not have, which is what the item's
"samples from more than one class of machine" was blocked on. It is the cores
axis only: four cores masked out of a large machine keep that machine's whole
last-level cache and memory controller, so nothing here samples a genuinely
low-bandwidth machine, and the constant this is aimed at
(`core/shares.py` `PREVIEW_WORKERS`) is justified as a *bandwidth* property.
A sweep that forgot this would report the strongest possible evidence for the
weakest of its axes.

**Nothing here belongs in the test suite.** Setting process affinity is global
state with no scope, so a sweep running beside anything else invalidates both.
`cli/sweep_cmd.py` is the entry point for that reason, not for convenience.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from statistics import median

import psutil

from sieve.core.machine import cpu_classes


class AffinityUnavailableError(RuntimeError):
    """Pinning was asked for and the platform refused.

    Raised rather than falling back to an unpinned reading, which would be a
    sample labelled with a core set it was not taken on — the machine axis
    silently becoming noise while the report still names it.
    """


@dataclass(frozen=True, slots=True)
class CoreSet:
    """CPUs a cell is pinned to, and what to call them in a report."""

    label: str
    cpus: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.cpus:
            raise ValueError(f"core set {self.label!r} is empty")


@dataclass(frozen=True, slots=True)
class Cell:
    """One point in the design: a core set and a worker count."""

    cores: CoreSet
    workers: int


@dataclass(frozen=True, slots=True)
class Reading:
    """Every sample taken at one cell, in the order they were taken."""

    cell: Cell
    samples: tuple[float, ...]

    @property
    def best(self) -> float:
        """The capability reading — what this configuration can do.

        `tests/bench/gate.py` argues the choice between this and `typical` at
        length and the argument is the same one here; a sweep reports both
        because which claim is being made is the *caller's* question, and a
        surface that offered one would have decided it for them.
        """
        return min(self.samples)

    @property
    def typical(self) -> float:
        """The reading a session actually gets, disturbances included."""
        return median(self.samples)


def class_core_sets(classes: dict[int, int] | None = None) -> tuple[CoreSet, ...]:
    """One core set per performance class, plus the unpinned whole allocation.

    On a uniform machine this is a single class and the result is two sets that
    happen to hold the same CPUs — deliberately not deduplicated, because
    "pinned to every core" and "not pinned at all" are different treatments
    even when the mask matches: the second permits the scheduler to migrate,
    and migration is the effect being measured.
    """
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
    """`source` truncated to each size, for the core-count axis.

    Truncated from the front rather than sampled, so a size-4 set is a subset
    of the size-8 set: the two readings then differ by core count alone, and a
    difference cannot be a different draw of cores.
    """
    out: list[CoreSet] = []
    for size in sorted({int(size) for size in sizes}):
        if 0 < size <= len(source.cpus):
            out.append(CoreSet(label=f"{source.label}[:{size}]", cpus=source.cpus[:size]))
    return tuple(out)


def design(cores: Sequence[CoreSet], workers: Sequence[int]) -> tuple[Cell, ...]:
    """The full factorial, skipping cells that ask for more workers than cores.

    Skipped rather than clamped: a clamped cell would report the 8-worker
    reading under the label 16, and two cells claiming different treatments
    while holding the same number is how a surface acquires a plateau nothing
    in the machine put there.
    """
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
    """Measure `objective` at every cell, `repeats` times, interleaved.

    **Interleaved, not blocked, and this is the whole reason the function
    exists rather than a nested loop at the call site.** Blocked runs of the
    density surface on the reference machine read 82-87 ms for eight readings
    and 100-147 ms for every reading after, with no condition changed — the
    scheduler migrates a thread off the performance cores as it accumulates
    runtime, so whichever treatment ran first got the fast cores and the
    finding would have been about running order. Round-robin spreads that
    drift across all cells instead of loading it onto the ones measured late.
    It does not remove the drift; nothing at this layer can. It stops the drift
    from having a preferred cell.

    `warmup` runs one unrecorded pass per cell first, because the first call
    into a cold path measures import, allocation, and page faults that no
    later call pays.

    Raises:
        AffinityUnavailableError: if the platform will not pin, or refuses a
            mask. The partial results are discarded — a sweep missing the cells
            the platform declined is a surface with a hole in it that its own
            table cannot show.
    """
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
    """Restrict `process` to the cell's cores, or refuse.

    `ValueError` is in the catch because psutil validates the mask itself and
    raises it for a CPU the machine does not have — a plain `ValueError` from
    three frames down is indistinguishable at the call site from a bug in the
    design, and both would abort the sweep with no statement of which.
    """
    try:
        process.cpu_affinity(list(cell.cores.cpus))
    except (AttributeError, NotImplementedError, psutil.Error, OSError, ValueError) as error:
        raise AffinityUnavailableError(
            f"could not pin to {cell.cores.label} ({list(cell.cores.cpus)}): {error}"
        ) from error


def curvature(readings: Sequence[Reading]) -> dict[str, float]:
    """Spread of the best reading across worker counts, per core set.

    The one number the controller question turns on, and it is a ratio rather
    than a difference so it survives comparison between machines: 1.0 is a
    worker count that changes nothing, and a controller on a core set reading
    near 1.0 can only oscillate, since there is no gain for it to act on.
    A core set with a single cell is absent rather than 1.0 — one point has no
    spread, and reporting it as flat would be an unmeasured claim.
    """
    by_label: dict[str, list[float]] = {}
    for reading in readings:
        by_label.setdefault(reading.cell.cores.label, []).append(reading.best)
    return {
        label: max(values) / min(values)
        for label, values in by_label.items()
        if len(values) > 1 and min(values) > 0.0
    }
