"""The bound on the Block spin box, held up by the measurement it claims.

`gui/density_plot.MAX_BLOCKS` is not a number somebody liked. It is the largest
`B` the density surface can be rebuilt at inside the `density_rebuild` budget,
and `gui/block_spin.BlockSpinBox` refuses every block size implying more. That
makes this file the producer rule 4 requires: without it the widget's refusal
threshold would be a magic number, and with it the threshold is a ceiling that
fails loudly the day the binning gets slower.

**The shape is the reference window at exactly the bound**, not the reference
footage's own grid. `T = 600` is the working window the graph budgets are
written against (`docs/findings/2026.07.27-the-density-histogram-was-a-scatter.md`
measured 599); `B = MAX_BLOCKS` is the worst case the control still admits. A
benchmark at a comfortable block size would pass forever and protect nothing —
the whole failure this bound exists for lives at the edge of the legal range.

The other half of the claim — that one block *above* the bound is refused rather
than binned — is in `tests/gui/test_density_binning.py`, not here. It is not a
timing, and `--benchmark-only` would skip it in this session, which is the one
place a bound needs to be checked least conditionally.
"""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Protocol

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from pytestqt.qtbot import QtBot

from sieve.bench.budgets import check
from sieve.gui.density_plot import MAX_BLOCKS, DensityPlot

pytestmark = [pytest.mark.gui, pytest.mark.benchmark]

#: The working window the in-pipeline graph budgets are written against.
REFERENCE_FRAMES = 600

ROUNDS = 3


class Benchmark(Protocol):
    """The slice of pytest-benchmark's fixture used here — see
    `test_perf_regression.py` for why the shape is declared rather than
    inferred."""

    def pedantic(self, target: Callable[[], None], *, rounds: int) -> object: ...


def _band_power(frames: int, blocks: int) -> np.ndarray:
    """Band power shaped like the real thing: positive, orders of magnitude wide.

    The log1p axis is what the binning spends its time in, so a flat array
    would measure a different function than the one the tab calls.
    """
    rng = np.random.default_rng(7)
    return (10.0 ** rng.uniform(-2.0, 3.0, (frames, blocks))).astype(np.float32)


def test_the_largest_admitted_block_count_rebuilds_within_budget(
    benchmark: Benchmark, qtbot: QtBot
) -> None:
    """`set_series` at `B = MAX_BLOCKS` over the reference window.

    A fresh array per round on purpose: the identity cache would otherwise
    make every round after the first measure a repaint, which is real and is
    not the interval this budget names.
    """
    plot = DensityPlot()
    qtbot.addWidget(plot)
    plot.resize(900, 200)
    samples: list[float] = []
    # Built up front, outside every round: generating them is more expensive
    # than the binning under test, and a round that included it would report a
    # number the budget was never written about.
    arrays = [_band_power(REFERENCE_FRAMES, MAX_BLOCKS) for _ in range(ROUNDS)]

    def once() -> None:
        m = arrays.pop()
        started = perf_counter()
        plot.set_series(m)
        samples.append((perf_counter() - started) * 1000.0)

    benchmark.pedantic(once, rounds=ROUNDS)
    check("density_rebuild", min(samples))
