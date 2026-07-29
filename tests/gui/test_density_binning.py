













from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray
from pytestqt.qtbot import QtBot

from sieve.gui import density_plot
from sieve.gui.density_plot import DensityPlot, bin_counts

pytestmark = pytest.mark.gui

BLOCKS = 64


class TestTheDensityHistogramCountsEveryBlockOnce:




    def test_each_frame_bins_all_of_its_blocks_and_no_more(self) -> None:









        rng = np.random.default_rng(3)
        m = rng.uniform(0.0, 1000.0, (40, BLOCKS)).astype(np.float32)
        counts = bin_counts(m, float(m.max()))
        assert counts.shape[1] == 40
        np.testing.assert_array_equal(counts.sum(axis=0), np.full(40, BLOCKS, np.float32))

    def test_the_loudest_value_lands_in_the_top_bin_and_zero_in_the_bottom(self) -> None:







        m = np.array([[0.0, 500.0, 1000.0]], np.float32)
        counts = bin_counts(m, 1000.0)
        assert counts[-1, 0] == 1.0
        assert counts[0, 0] == 1.0

    def test_a_non_finite_block_is_floored_rather_than_wrapped(self) -> None:







        m = np.array([[np.nan, 10.0]], np.float32)
        counts = bin_counts(m, 10.0)
        assert counts.sum() == 2.0
        assert counts[0, 0] == 1.0
        assert counts[-1, 0] == 1.0


class TestTheDensitySurfaceIsBuiltOnlyWhenItsArrayMoves:
    def test_the_same_array_twice_bins_once(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:








        plot = DensityPlot()
        qtbot.addWidget(plot)
        plot.resize(800, 200)
        calls: list[int] = []
        real = density_plot.bin_counts

        def counted(
            band_power: NDArray[np.float32], value_max: float, bins: int = 96
        ) -> NDArray[np.float32]:
            calls.append(1)
            return real(band_power, value_max, bins)

        monkeypatch.setattr(density_plot, "bin_counts", counted)
        m = np.random.default_rng(5).uniform(0.0, 100.0, (32, BLOCKS)).astype(np.float32)

        plot.set_series(m)
        plot.set_series(m)
        plot.set_series(m, solo=m[:, 0])
        assert len(calls) == 1

    def test_a_new_array_rebuilds_the_axis_with_it(self, qtbot: QtBot) -> None:






        plot = DensityPlot()
        qtbot.addWidget(plot)
        plot.resize(800, 200)
        quiet = np.full((32, BLOCKS), 10.0, np.float32)
        loud = np.full((32, BLOCKS), 10_000.0, np.float32)

        plot.set_series(quiet)
        plot.set_band(0.0, 10.0)
        y_quiet = plot.handle_y("hi")
        plot.set_series(loud)
        plot.set_band(0.0, 10.0)
        assert plot.handle_y("hi") != y_quiet
