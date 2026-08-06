"""The measured rescale cost model, independent of Qt widgets."""

from __future__ import annotations

import math

import pytest

from sieve.core.types import WallTime
from sieve.gui.rescale_cost import (
    RescaleCostHistory,
    RescaleCostSample,
    fit_rescale_cost,
    format_rescale_cost,
)


def sample(scale: float, seconds_per_frame: float, *, context: str = "same") -> RescaleCostSample:
    frames = 100
    return RescaleCostSample(
        scale=scale,
        frames=frames,
        wall=WallTime(seconds_per_frame * frames),
        context=context,
    )


def test_two_scales_fit_the_fixed_floor_and_knee() -> None:
    """The v1 model is fitted from wall time moving with scale squared."""
    fixed = 0.010
    per_pixel = 0.030
    fit = fit_rescale_cost(
        [
            sample(1.0, fixed + per_pixel),
            sample(0.5, fixed + per_pixel * 0.25),
        ]
    )

    assert fit is not None
    assert not fit.provisional
    assert fit.fixed_per_frame.seconds == pytest.approx(fixed)
    assert fit.per_pixel_per_frame.seconds == pytest.approx(per_pixel)
    projected = fit.projected_seconds_per_frame(0.25)
    assert projected is not None
    assert projected.seconds == pytest.approx(fixed + per_pixel * 0.25**2)
    assert fit.knee_scale() == pytest.approx(math.sqrt(fixed / per_pixel))
    assert fit.elasticity(1.0) == pytest.approx(1.5)


def test_one_scale_is_provisional_and_prints_no_time_or_knee() -> None:
    """A single pass cannot split decode floor from per-pixel work."""
    fit = fit_rescale_cost([sample(0.5, 0.020)])

    assert fit is not None
    assert fit.provisional
    assert fit.projected_seconds_per_frame(0.5) is None
    assert fit.knee_scale() is None
    label = format_rescale_cost(fit, 0.5)
    assert "needs another scale" in label
    assert "ms/fr" not in label
    assert "knee" not in label


def test_context_change_clears_previous_samples() -> None:
    """Samples from two footage/window contexts must not share one fit."""
    history = RescaleCostHistory()
    history.add(sample(1.0, 0.040, context="a"))
    history.add(sample(0.5, 0.020, context="a"))

    assert history.fit is not None and not history.fit.provisional

    history.prepare("b")

    assert history.samples == ()
    assert history.fit is None
