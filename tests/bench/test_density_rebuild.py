




















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


REFERENCE_FRAMES = 600




REFERENCE_BLOCKS = 16_384

ROUNDS = 3


class Benchmark(Protocol):




    def pedantic(self, target: Callable[[], object], *, rounds: int) -> object: ...


def _band_power(frames: int, blocks: int, seed: int = 7) -> np.ndarray:





    rng = np.random.default_rng(seed)
    return (10.0 ** rng.uniform(-2.0, 3.0, (frames, blocks))).astype(np.float32)


def test_the_reference_block_count_rebuilds_within_budget(benchmark: Benchmark) -> None:

    samples: list[float] = []










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



    within_budget("density_rebuild", samples, resample=once, statistic=BEST)
