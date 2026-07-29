"""The density surface: what it counts, and when it is rebuilt at all.

Two separate claims, and they fail for separate reasons. `bin_counts` replaced
an `np.add.at` scatter — 18x slower, and 1.5 GB of index arrays allocated per
call — so what needs pinning is that the cheaper binning still puts every block
in exactly one bin and still spans the axis it labels. The identity cache is the
other half and the larger one: the cheap tier hands the same `band_power` object
back on every mouse-move, so re-binning it is an O(T x B) pass inside a 50 ms
budget for a picture that cannot have changed.

The speed itself is not asserted here; doing so would turn a correctness test
into a machine-dependent benchmark.
"""

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
    """`bin_counts` replaced an `np.add.at` scatter that was 18x slower and
    allocated 1.5 GB of index arrays per drag tick. These pin what the rewrite
    could plausibly have broken; the speed itself is a finding, not a gate."""

    def test_each_frame_bins_all_of_its_blocks_and_no_more(self) -> None:
        """Column sums are B, every frame.

        The `minlength` and the clip are both load-bearing here: a bin index
        off the top would make `bincount` return a longer row than the array it
        is assigned into, and a frame whose values all land in one bin would
        return a shorter one. Either way some blocks stop being counted, and a
        density plot that quietly drops population is exactly the "unexamined
        must not render as quiet" failure.
        """
        rng = np.random.default_rng(3)
        m = rng.uniform(0.0, 1000.0, (40, BLOCKS)).astype(np.float32)
        counts = bin_counts(m, float(m.max()))
        assert counts.shape[1] == 40
        np.testing.assert_array_equal(counts.sum(axis=0), np.full(40, BLOCKS, np.float32))

    def test_the_loudest_value_lands_in_the_top_bin_and_zero_in_the_bottom(self) -> None:
        """The axis still spans what it claims to.

        A rewrite that dropped the `- 1` or the clip would put the maximum one
        bin past the end or one short of it, and the band handles — which read
        the same log1p mapping — would then point at a different row of the
        surface than the one they highlight.
        """
        m = np.array([[0.0, 500.0, 1000.0]], np.float32)
        counts = bin_counts(m, 1000.0)
        assert counts[-1, 0] == 1.0
        assert counts[0, 0] == 1.0

    def test_a_non_finite_block_is_floored_rather_than_wrapped(self) -> None:
        """NaN goes to the bottom bin, not the brightest one.

        This is the behaviour `np.add.at` got wrong for free: a NaN through
        `astype(int32)` is a large negative, which a scatter happily wraps onto
        the *top* of the array — painting an undefined block as the loudest
        thing in the window.
        """
        m = np.array([[np.nan, 10.0]], np.float32)
        counts = bin_counts(m, 10.0)
        assert counts.sum() == 2.0
        assert counts[0, 0] == 1.0
        assert counts[-1, 0] == 1.0


class TestTheDensitySurfaceIsBuiltOnlyWhenItsArrayMoves:
    def test_the_same_array_twice_bins_once(
        self, qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The cheap tier's whole point, at this widget's boundary.

        A value-band drag re-derives from the retained `band_power` and calls
        `set_series` with the identical object on every mouse-move. Re-binning
        it would put an O(T x B) pass inside a 50 ms budget — measured at 1.5 s
        on the reference stress workload — for a picture that cannot have
        changed.
        """
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
        """The other half: the cache must not survive an expensive derive.

        A frequency-band commit allocates a fresh `band_power` with its own
        scale, and a stale surface would leave the value handles pointing at
        rows of a picture taken under the previous band.
        """
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
