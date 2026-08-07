"""Measured wall-clock model for the live rescale knob.

`FilterSpec.cost` stays a machine-independent work declaration. This module is
the other side: observations from completed preview renders on the current
footage and current machine. The only fitted shape is v1's measured one:

    seconds_per_frame(s) = F + M*s**2

where `F` is the fixed whole-frame decode/source floor and `M` is the
scale-sensitive downstream work at full resolution.

Three things can make a sample set unable to state that curve, and each refuses
with its own reason rather than producing a number:

- **One scale.** Two unknowns need two abscissae.
- **Mixed cache regimes.** `PreviewSession` serves unchanged node outputs from
  the store, so a render that reused the prefix above the rescale node skipped
  the decode that `F` is supposed to measure. Wall times taken under different
  reuse are not measurements of the same quantity, and pooling them drives `F`
  — and therefore the knee, which is `sqrt(F/M)` — toward zero.
- **Data that contradicts the model.** A negative `M` says cost fell as
  resolution rose and a negative `F` says the curve passes below the origin;
  both mean noise dominated. Clamping either to zero and reporting the result
  turns a failed measurement into a confident label, which is the one thing
  rule 6 forbids.

Two distinct scales fit the two parameters exactly, which leaves no residual to
test the model against. Such a fit is reported but not `validated`, and the
readout marks it as an estimate. A third scale is what makes the shape
falsifiable, and from there `fit_quality` can refuse a fit the samples do not
support.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from sieve.core.types import WallTime

SCALE_DIGITS = 6

#: How far two samples' cache reuse may differ and still measure the same
#: quantity. Small because reuse is a share of node outputs, not a timing: a
#: tenth of the graph appearing from the store is already a different run.
REUSE_SPREAD_LIMIT = 0.10

#: Share of the observed variance the fitted curve must explain once there are
#: enough scales to compute a residual at all. Lenient, because preview timings
#: on a contended machine are noisy and the alternative to a rough fit here is
#: no readout, not a better one.
MIN_FIT_QUALITY = 0.80


@dataclass(frozen=True, slots=True)
class Provisional:
    """Why no curve is being reported, in the words the readout will use."""

    #: Short phrase for the inline label, after "cost: ".
    label: str
    #: The sentence the tooltip states instead of a fitted curve.
    detail: str


NEEDS_ANOTHER_SCALE = Provisional(
    label="needs another scale",
    detail=(
        "One scale has been timed. Another scale is required before SIEVE can "
        "separate the fixed decode/source floor from scale-sensitive work."
    ),
)

MIXED_CACHE_REUSE = Provisional(
    label="cache reuse differs between scales",
    detail=(
        "The timed renders served different shares of the chain from the store, "
        "so their wall times do not measure the same work. Re-render each scale "
        "again to compare warm passes."
    ),
)

CONTRADICTS_MODEL = Provisional(
    label="timings contradict the model",
    detail=(
        "The measured wall times imply a negative fixed floor or negative "
        "scale-sensitive work, which means noise dominated them. No curve is "
        "reported; time more scales."
    ),
)

UNEXPLAINED_SPREAD = Provisional(
    label="timings too scattered to fit",
    detail=(
        f"The fitted F + M*s^2 curve explains less than {MIN_FIT_QUALITY:.0%} of "
        "the spread in the timed renders, so it is not a description of this "
        "footage on this machine."
    ),
)


@dataclass(frozen=True, slots=True)
class RescaleCostSample:
    """One completed window render in the context it measured."""

    scale: float
    frames: int
    wall: WallTime
    context: str
    #: `PreviewRender.reuse` for this render: the share of node outputs served
    #: from the store rather than computed. Recorded because it decides whether
    #: two samples are comparable, not because it is displayed.
    reuse: float = 0.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.scale) or self.scale <= 0.0:
            raise ValueError(f"scale must be positive and finite, got {self.scale!r}")
        if self.frames <= 0:
            raise ValueError(f"frames must be positive, got {self.frames}")
        if not math.isfinite(self.wall.seconds) or self.wall.seconds < 0.0:
            raise ValueError(
                f"wall time must be finite and non-negative, got {self.wall.seconds!r}"
            )
        if not 0.0 <= self.reuse <= 1.0:
            raise ValueError(f"reuse is a share from 0.0 to 1.0, got {self.reuse!r}")

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
    #: The refusal, or None when a curve is being reported.
    provisional: Provisional | None
    #: Whether enough distinct scales exist to leave a residual the fit had to
    #: survive. A two-scale fit passes through both points by construction.
    validated: bool = False

    def projected_seconds_per_frame(self, scale: float) -> WallTime | None:
        """Projected wall cost, withheld while the fit is provisional."""
        if self.provisional is not None:
            return None
        return WallTime(self.fixed_per_frame.seconds + self.per_pixel_per_frame.seconds * scale**2)

    def knee_scale(self, *, min_scale: float = 0.05) -> float | None:
        """The scale where 1% less resolution stops buying 1% less time."""
        if (
            self.provisional is not None
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
        return _refused(NEEDS_ANOTHER_SCALE, len(usable))
    reuses = [sample.reuse for sample in usable]
    if max(reuses) - min(reuses) > REUSE_SPREAD_LIMIT:
        return _refused(MIXED_CACHE_REUSE, len(usable))

    xs = [sample.scale**2 for sample in usable]
    ys = [sample.seconds_per_frame for sample in usable]
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    if sxx <= 0.0:
        return _refused(NEEDS_ANOTHER_SCALE, count)
    per_pixel = sxy / sxx
    fixed = mean_y - per_pixel * mean_x
    if per_pixel <= 0.0 or fixed < 0.0:
        return _refused(CONTRADICTS_MODEL, count)

    validated = len(scales) >= 3
    if validated and _fit_quality(xs, ys, mean_y, fixed, per_pixel) < MIN_FIT_QUALITY:
        return _refused(UNEXPLAINED_SPREAD, count)
    return RescaleCostFit(
        fixed_per_frame=WallTime(fixed),
        per_pixel_per_frame=WallTime(per_pixel),
        n_samples=count,
        provisional=None,
        validated=validated,
    )


def _refused(reason: Provisional, n_samples: int) -> RescaleCostFit:
    return RescaleCostFit(
        fixed_per_frame=WallTime(0.0),
        per_pixel_per_frame=WallTime(0.0),
        n_samples=n_samples,
        provisional=reason,
    )


def _fit_quality(
    xs: list[float], ys: list[float], mean_y: float, fixed: float, per_pixel: float
) -> float:
    """Share of the spread in `ys` the fitted line accounts for.

    One for a sample set with no spread at all: identical timings at different
    scales are a real (if flat) observation, not a fit that failed.
    """
    total = sum((y - mean_y) ** 2 for y in ys)
    if total <= 0.0:
        return 1.0
    residual = sum((y - (fixed + per_pixel * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    return 1.0 - residual / total


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
    if fit.provisional is not None:
        return f"cost: {fit.provisional.label}"
    projected = fit.projected_seconds_per_frame(scale)
    if projected is None:
        return f"cost: {NEEDS_ANOTHER_SCALE.label}"
    knee = fit.knee_scale()
    knee_text = "no knee" if knee is None else f"knee {knee:.2f}"
    # A two-scale fit passes through its points by construction, so the number
    # is an estimate the samples could not have contradicted.
    mark = "" if fit.validated else "~"
    return f"cost {mark}{projected.milliseconds:.1f} ms/fr; {knee_text}"
