"""The measured rescale cost model, independent of Qt widgets."""

from __future__ import annotations

import math

import pytest

from sieve.core.types import WallTime
from sieve.gui.rescale_cost import (
    CONTRADICTS_MODEL,
    MIXED_CACHE_REUSE,
    NEEDS_ANOTHER_SCALE,
    UNEXPLAINED_SPREAD,
    RescaleCostHistory,
    RescaleCostSample,
    fit_rescale_cost,
    format_rescale_cost,
)


def sample(
    scale: float,
    seconds_per_frame: float,
    *,
    context: str = "same",
    reuse: float = 0.0,
) -> RescaleCostSample:
    frames = 100
    return RescaleCostSample(
        scale=scale,
        frames=frames,
        wall=WallTime(seconds_per_frame * frames),
        context=context,
        reuse=reuse,
    )


def curve(scale: float, fixed: float, per_pixel: float) -> float:
    return fixed + per_pixel * scale**2


def test_two_scales_fit_the_curve_but_cannot_validate_it() -> None:
    """The v1 model is fitted from wall time moving with scale squared."""
    fixed = 0.010
    per_pixel = 0.030
    fit = fit_rescale_cost(
        [
            sample(1.0, curve(1.0, fixed, per_pixel)),
            sample(0.5, curve(0.5, fixed, per_pixel)),
        ]
    )

    assert fit is not None
    assert fit.provisional is None
    assert fit.fixed_per_frame.seconds == pytest.approx(fixed)
    assert fit.per_pixel_per_frame.seconds == pytest.approx(per_pixel)
    projected = fit.projected_seconds_per_frame(0.25)
    assert projected is not None
    assert projected.seconds == pytest.approx(curve(0.25, fixed, per_pixel))
    assert fit.knee_scale() == pytest.approx(math.sqrt(fixed / per_pixel))
    assert fit.elasticity(1.0) == pytest.approx(1.5)

    # Both points lie on the fitted line by construction, so the readout must
    # not present the projection as something the samples could have refuted.
    assert not fit.validated
    assert format_rescale_cost(fit, 1.0) == "cost ~40.0 ms/fr; knee 0.58"


def test_a_third_scale_validates_the_fit_and_drops_the_estimate_mark() -> None:
    """A residual the curve had to survive is what makes the number a claim."""
    fixed = 0.010
    per_pixel = 0.030
    fit = fit_rescale_cost(
        [sample(scale, curve(scale, fixed, per_pixel)) for scale in (1.0, 0.5, 0.25)]
    )

    assert fit is not None and fit.provisional is None
    assert fit.validated
    assert format_rescale_cost(fit, 1.0) == "cost 40.0 ms/fr; knee 0.58"


def test_one_scale_is_provisional_and_prints_no_time_or_knee() -> None:
    """A single pass cannot split decode floor from per-pixel work."""
    fit = fit_rescale_cost([sample(0.5, 0.020)])

    assert fit is not None
    assert fit.provisional is NEEDS_ANOTHER_SCALE
    assert fit.projected_seconds_per_frame(0.5) is None
    assert fit.knee_scale() is None
    label = format_rescale_cost(fit, 0.5)
    assert "needs another scale" in label
    assert "ms/fr" not in label
    assert "knee" not in label


def test_samples_taken_under_different_cache_reuse_do_not_fit() -> None:
    """A warm render skipped the decode the fixed floor is meant to measure.

    Pooling it with a cold one drives the fitted floor — and the knee, which is
    its square root over `M` — toward zero for a reason that is not the scale.
    """
    cold = sample(1.0, 0.040, reuse=0.0)
    warm = sample(0.5, 0.010, reuse=0.75)

    fit = fit_rescale_cost([cold, warm])

    assert fit is not None
    assert fit.provisional is MIXED_CACHE_REUSE
    assert fit.projected_seconds_per_frame(0.5) is None
    assert "cache reuse" in format_rescale_cost(fit, 0.5)

    matched = fit_rescale_cost([cold, sample(0.5, 0.020, reuse=0.05)])
    assert matched is not None and matched.provisional is None


def test_timings_that_contradict_the_model_refuse_rather_than_clamp() -> None:
    """Cost falling as resolution rises is noise, not a zero-cost filter."""
    fit = fit_rescale_cost([sample(1.0, 0.010), sample(0.5, 0.040)])

    assert fit is not None
    assert fit.provisional is CONTRADICTS_MODEL
    assert fit.projected_seconds_per_frame(1.0) is None
    assert fit.knee_scale() is None


def test_a_negative_fixed_floor_refuses_rather_than_refitting_through_zero() -> None:
    """A curve passing below the origin fails the model it claims to be."""
    fit = fit_rescale_cost([sample(1.0, 0.100), sample(0.5, 0.010)])

    assert fit is not None
    assert fit.provisional is CONTRADICTS_MODEL


def test_scattered_timings_refuse_once_a_residual_can_be_computed() -> None:
    """Three scales can disagree with the curve; two never can."""
    scattered = [
        sample(1.0, 0.040),
        sample(0.5, 0.038),
        sample(0.25, 0.002),
    ]
    fit = fit_rescale_cost(scattered)

    assert fit is not None
    assert fit.provisional is UNEXPLAINED_SPREAD
    assert "scattered" in format_rescale_cost(fit, 0.5)


def test_context_change_clears_previous_samples() -> None:
    """Samples from two footage/window contexts must not share one fit."""
    history = RescaleCostHistory()
    history.add(sample(1.0, 0.040, context="a"))
    history.add(sample(0.5, 0.020, context="a"))

    assert history.fit is not None and history.fit.provisional is None

    history.prepare("b")

    assert history.samples == ()
    assert history.fit is None


def test_reuse_outside_a_share_is_refused_at_construction() -> None:
    """`reuse` is `PreviewRender.reuse`, and nothing else is a share."""
    with pytest.raises(ValueError, match="share"):
        sample(0.5, 0.020, reuse=1.5)
