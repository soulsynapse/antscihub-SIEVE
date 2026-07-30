"""What the density surface costs at the reference block count.

`density_rebuild` used to be the producer for a *refusal*: `MAX_BLOCKS` was the
largest B the surface could be built at inside the budget and the Block spin box
declined everything implying more. Do not restore that cap: block count is a
scientific choice, and the binning no longer runs on the GUI thread, so a large
one costs time rather than a frozen window.

So this file's claim changed and its shape did not. The budget is now the
*attribution* threshold — the point past which `gui/graph_hud.py` names this
span as the dominant cost — and a threshold nothing measures is as useless for
attributing as it was for refusing. `B = REFERENCE_BLOCKS` is the reference
workload the 100 ms ceiling was written against (rule 4: budgets are scoped to
the reference workload), not a bound on anything a user may enter.

**It times `density_surface`, not `set_series`.** That is where the work is
now, on `gui/detector_worker.py`'s thread; the widget's remaining job is a
`QImage` wrap, which is not what the ceiling is about. `T = 600` is the working
window the graph budgets are written against.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from time import perf_counter
from typing import Protocol

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from sieve.gui.density_plot import density_surface
from tests.bench.gate import BEST, within_budget

pytestmark = [pytest.mark.gui, pytest.mark.benchmark]

#: The working window the in-pipeline graph budgets are written against.
REFERENCE_FRAMES = 600

#: The block count the 100 ms ceiling was measured at — a 128x128 grid, and the
#: number the removed cap used to be. Kept as the reference point so the
#: readings stay comparable to every finding written before the cap came off.
REFERENCE_BLOCKS = 16_384

ROUNDS = 3


class Benchmark(Protocol):
    """The slice of pytest-benchmark's fixture used here — see
    `test_perf_regression.py` for why the shape is declared rather than
    inferred."""

    def pedantic(self, target: Callable[[], object], *, rounds: int) -> object: ...


def _band_power(frames: int, blocks: int, seed: int = 7) -> np.ndarray:
    """Band power shaped like the real thing: positive, orders of magnitude wide.

    The log1p axis is what the binning spends its time in, so a flat array
    would measure a different function than the one the tab calls.
    """
    rng = np.random.default_rng(seed)
    return (10.0 ** rng.uniform(-2.0, 3.0, (frames, blocks))).astype(np.float32)


def test_the_reference_block_count_rebuilds_within_budget(benchmark: Benchmark) -> None:
    """`density_surface` at the reference window and block count."""
    samples: list[float] = []
    # `ROUNDS` up front and no more, and the count is load-bearing. One array is
    # 600 x 16384 float32 = 39 MB, and the binning is memory-bandwidth bound,
    # so holding nine of them to pre-build every retry
    # slows the thing under test by half again. A retry generates its array
    # instead, before the clock starts, and lets it go afterwards — so the
    # resident footprint is the same on the tenth reading as on the first.
    #
    # Built outside the timed region either way: generating is more expensive
    # than the binning, and a round that included it would report a number the
    # budget was never written about.
    arrays = [_band_power(REFERENCE_FRAMES, REFERENCE_BLOCKS, seed) for seed in range(ROUNDS)]
    seeds = itertools.count(ROUNDS)

    def once() -> float:
        series = (
            arrays.pop() if arrays else _band_power(REFERENCE_FRAMES, REFERENCE_BLOCKS, next(seeds))
        )
        started = perf_counter()
        density_surface(series)
        elapsed = (perf_counter() - started) * 1000.0
        samples.append(elapsed)
        return elapsed

    benchmark.pedantic(once, rounds=ROUNDS)
    # `BEST`, because this is a capability bound: the claim is that the
    # reference block count *can* be binned inside the budget, and every sample
    # above the minimum is that one plus whatever else the machine was doing.
    within_budget("density_rebuild", samples, resample=once, statistic=BEST)
