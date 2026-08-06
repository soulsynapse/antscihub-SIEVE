"""Measured wall-clock model for the live rescale knob.

`FilterSpec.cost` stays a machine-independent work declaration. This module is
the other side: observations from completed preview renders on the current
footage and current machine. The only fitted shape is v1's measured one:

    seconds_per_frame(s) = F + M*s**2

where `F` is the fixed whole-frame decode/source floor and `M` is the
scale-sensitive downstream work at full resolution. A single scale cannot split
those two terms, so the model reports itself as provisional and refuses to
project a number or a knee.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from sieve.core.types import WallTime

SCALE_DIGITS = 6


@dataclass(frozen=True, slots=True)
class RescaleCostSample:
    """One completed window render in the context it measured."""

    scale: float
    frames: int
    wall: WallTime
    context: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.scale) or self.scale <= 0.0:
            raise ValueError(f"scale must be positive and finite, got {self.scale!r}")
        if self.frames <= 0:
            raise ValueError(f"frames must be positive, got {self.frames}")
        if not math.isfinite(self.wall.seconds) or self.wall.seconds < 0.0:
            raise ValueError(
                f"wall time must be finite and non-negative, got {self.wall.seconds!r}"
            )

    @property
    def seconds_per_frame(self) -> float:
        """Wall seconds charged to one delivered frame."""
        return self.wall.seconds / self.frames


@dataclass(frozen=True, slots=True)
class RescaleCostFit:
    """A fit of `F + M*s**2` for one measured context."""

    fixed_per_frame: WallTime
    per_pixel_per_frame: WallTime
    n_samples: int
    provisional: bool

    def projected_seconds_per_frame(self, scale: float) -> WallTime | None:
        """Projected wall cost, withheld while the fit is provisional."""
        if self.provisional:
            return None
        return WallTime(self.fixed_per_frame.seconds + self.per_pixel_per_frame.seconds * scale**2)

    def knee_scale(self, *, min_scale: float = 0.05) -> float | None:
        """The scale where 1% less resolution stops buying 1% less time."""
        if (
            self.provisional
            or self.fixed_per_frame.seconds <= 0.0
            or self.per_pixel_per_frame.seconds <= 0.0
        ):
            return None
        knee = math.sqrt(self.fixed_per_frame.seconds / self.per_pixel_per_frame.seconds)
        if knee >= 1.0:
            return None
        return max(min_scale, knee)

    def elasticity(self, scale: float) -> float | None:
        """`d(log t) / d(log s)` for the fitted curve."""
        projected = self.projected_seconds_per_frame(scale)
        if projected is None or projected.seconds <= 0.0:
            return None
        return 2.0 * self.per_pixel_per_frame.seconds * scale**2 / projected.seconds


def fit_rescale_cost(samples: list[RescaleCostSample]) -> RescaleCostFit | None:
    """Fit the current context's samples, or report why no fit can be shown."""
    usable = [sample for sample in samples if sample.frames > 0 and sample.scale > 0.0]
    if not usable:
        return None
    scales = {round(sample.scale, SCALE_DIGITS) for sample in usable}
    if len(scales) < 2:
        return RescaleCostFit(
            fixed_per_frame=WallTime(0.0),
            per_pixel_per_frame=WallTime(0.0),
            n_samples=len(usable),
            provisional=True,
        )

    xs = [sample.scale**2 for sample in usable]
    ys = [sample.seconds_per_frame for sample in usable]
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    per_pixel = sxy / sxx if sxx > 0.0 else 0.0
    fixed = mean_y - per_pixel * mean_x
    if per_pixel < 0.0:
        per_pixel = 0.0
        fixed = mean_y
    if fixed < 0.0:
        fixed = 0.0
        per_pixel = mean_y / mean_x if mean_x > 0.0 else 0.0
    return RescaleCostFit(
        fixed_per_frame=WallTime(fixed),
        per_pixel_per_frame=WallTime(per_pixel),
        n_samples=count,
        provisional=False,
    )


def _sample_list() -> list[RescaleCostSample]:
    return []


@dataclass(slots=True)
class RescaleCostHistory:
    """Measured samples for one context; a context change clears the fit."""

    _context: str | None = None
    _samples: list[RescaleCostSample] = field(default_factory=_sample_list)

    def prepare(self, context: str) -> None:
        """Make `context` current, clearing samples from any previous one."""
        if context == self._context:
            return
        self._context = context
        self._samples.clear()

    def add(self, sample: RescaleCostSample) -> RescaleCostFit:
        """Record a completed render and return the current fit."""
        self.prepare(sample.context)
        self._samples.append(sample)
        fit = fit_rescale_cost(self._samples)
        if fit is None:
            raise RuntimeError("a just-added sample produced no fit")
        return fit

    def clear(self) -> None:
        """Drop every observation."""
        self._context = None
        self._samples.clear()

    @property
    def fit(self) -> RescaleCostFit | None:
        """The current fit, if any observations exist."""
        return fit_rescale_cost(self._samples)

    @property
    def samples(self) -> tuple[RescaleCostSample, ...]:
        """Observed samples, exposed for tests and diagnostics."""
        return tuple(self._samples)


def format_rescale_cost(fit: RescaleCostFit | None, scale: float) -> str:
    """Compact label text for the rescale row."""
    if fit is None:
        return "cost: timing pending"
    if fit.provisional:
        return "cost: needs another scale"
    projected = fit.projected_seconds_per_frame(scale)
    if projected is None:
        return "cost: needs another scale"
    knee = fit.knee_scale()
    knee_text = "no knee" if knee is None else f"knee {knee:.2f}"
    return f"cost {projected.milliseconds:.1f} ms/fr; {knee_text}"
