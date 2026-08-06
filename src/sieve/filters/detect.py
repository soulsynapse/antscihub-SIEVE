"""Detection as a discovered windowed filter.

The saved schema still carries `Project.detector` until the v6 graph migration,
so this module is the filter-owned spelling of the same parameters rather than
the destructive flip. It gives the detector an id, a params model, declared
I/O, a warmup refinement, and a CPU kernel on the normal shelf. The existing
full-series GUI and CSV derivations come through this module's compatibility
adapter so the filter owns the boundary without pretending the executor's
trailing window protocol can represent centered, non-causal whole-record
semantics.

The emitted product is a per-frame gate channel: one float32 value for the
target frame, `1` when detected, `0` when not detected, and `NaN` when disarmed.
Counts and intervals remain derived products of the compatibility layer today;
the later table-emitter item is where intervals become rows.
"""

from __future__ import annotations

import math
from typing import Any, Self

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, model_validator

from sieve.backend.dispatch import Backend, windowed_kernel
from sieve.core.filter_base import (
    ArraySpec,
    AuthoringGroup,
    CaptionPart,
    CostEstimate,
    ElementKind,
    ElementNames,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.ops.wavelet import (
    ALL_CORES,
    PAD_EFOLDINGS,
    band_indices,
    coi_edge_samples,
    default_freqs,
    morlet_power,
)
from sieve.core.pipeline_model import DetectorSettings
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameIndex, FrameSpan, WorkUnits
from sieve.detect.detector import DetectorUpdate
from sieve.detect.detector import detect as _detect_settings
from sieve.detect.detector import gate_to as _gate_to
from sieve.detect.detector import settled_for as _settled_for_settings

MAX_WINDOW_FRAMES = 600
MAX_FPS = 240.0
FloatArray = NDArray[np.floating[Any]]


def _wavelet_warmup_frames(fps: float, freq_band: tuple[float, float]) -> int:
    """History needed to keep the target out of the wavelet's padded edge."""
    freqs = default_freqs(fps)
    i, j = band_indices(freqs, freq_band[0], freq_band[1])
    edge = coi_edge_samples(freqs[i:j], fps)
    if edge.size == 0:
        return 0
    return math.ceil(float(edge.max()) * PAD_EFOLDINGS)


MAX_WARMUP_FRAMES = max(
    MAX_WINDOW_FRAMES - 1,
    _wavelet_warmup_frames(MAX_FPS, (0.0, math.inf)),
)


@register_filter(
    filter_id="detect",
    version="1.0.0",
    summary="Morlet band power, value-band count, and detection gate as a per-frame channel.",
    accepts=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    element=ElementKind.FRAME,
    element_names=ElementNames("frame", "frames"),
    cost=CostEstimate(
        # Windowed Morlet power and gate derivation over the largest declared
        # target window. Calibration decides how this work maps to wall time on
        # a target profile.
        work_per_megapixel=WorkUnits(float(MAX_WINDOW_FRAMES)),
        peak_bytes_per_input_byte=10.0,
    ),
    authoring_group=AuthoringGroup.DETECTION,
    mode=Mode.WINDOWED,
    settling_epsilon=0.0,
    primary_params=("freq_band", "value_band", "count_frac", "window_frames"),
    caption=(
        CaptionPart(label="freq", param="freq_band"),
        CaptionPart(label="value", param="value_band"),
        CaptionPart(label="count", param="count_frac"),
        CaptionPart(label="D", param="window_frames"),
    ),
)
class DetectParams(ParamsBase):
    """The detector's identity parameters, plus source fps for the wavelet bank."""

    fps: float = Field(default=30.0, gt=0.0, le=MAX_FPS)
    freq_band: tuple[float, float] = (0.0, math.inf)
    value_band: tuple[float, float] = (-math.inf, math.inf)
    count_frac: tuple[float, float] | None = None
    window_frames: int = Field(default=30, ge=1, le=MAX_WINDOW_FRAMES)
    centered: bool = True

    @classmethod
    def max_warmup_frames(cls) -> FrameCount:
        """Worst case over the legal detector window and frequency range."""
        return FrameCount(MAX_WARMUP_FRAMES)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        for name in ("freq_band", "value_band", "count_frac"):
            band: tuple[float, float] | None = getattr(self, name)
            if band is not None and band[0] > band[1]:
                raise ValueError(f"{name} must be ordered, got {band}")
        if self.freq_band[0] < 0:
            raise ValueError(f"freq_band must be non-negative, got {self.freq_band}")
        return self

    @classmethod
    def from_settings(cls, settings: DetectorSettings, *, fps: float) -> DetectParams:
        """The compatibility bridge from schema-v5 detector settings."""
        return cls(fps=fps, **settings.model_dump())

    def to_settings(self) -> DetectorSettings:
        """The schema-v5 spelling, for the compatibility detector layer."""
        return DetectorSettings(
            freq_band=self.freq_band,
            value_band=self.value_band,
            count_frac=self.count_frac,
            window_frames=self.window_frames,
            centered=self.centered,
        )

    def warmup_frames(self) -> FrameCount:
        """The larger of the D-window history and the wavelet edge history."""
        return FrameCount(
            max(self.window_frames - 1, _wavelet_warmup_frames(self.fps, self.freq_band))
        )


def detect_series(
    series: FloatArray,
    params: DetectParams,
    *,
    start_index: int | FrameIndex = 0,
    band_power: NDArray[np.float32] | None = None,
    workers: int,
) -> DetectorUpdate:
    """Derive the detector over a whole collected series through filter params.

    This is the parity-safe bridge for the GUI and `sieve detect --csv`: both
    callers need the same non-causal whole-record values the old
    `DetectorSettings` composition produced, while the executor's windowed
    kernel is intentionally trailing and per-target. Keeping the bridge here
    makes the filter id, params model, kernel, and compatibility derivation one
    owned surface.
    """
    return _detect_settings(
        _series2d(series),
        params.fps,
        params.to_settings(),
        start_index=int(start_index),
        band_power=band_power,
        workers=workers,
    )


def pooled_scalogram(
    series: FloatArray,
    params: DetectParams,
    *,
    workers: int,
) -> NDArray[np.float32]:
    """The pooled Morlet surface the GUI plots beside the detector output."""
    series2d = _series2d(series)
    freqs = default_freqs(params.fps)
    return morlet_power(series2d.mean(axis=1), params.fps, freqs, workers=workers)


def settled_for(frames: int, params: DetectParams, *, final: bool) -> int:
    """The safe detection frontier for `params` over `frames` collected rows."""
    return _settled_for_settings(frames, params.fps, params.to_settings(), final=final)


def gate_to(update: DetectorUpdate, settled: int, start_index: int | FrameIndex) -> DetectorUpdate:
    """Truncate a gate through the filter-owned compatibility boundary."""
    return _gate_to(update, settled, int(start_index))


@windowed_kernel(DetectParams, Backend.CPU)
def detect_cpu(span: FrameSpan, params: DetectParams) -> Frame:
    """Emit the target frame's gate as a scalar channel.

    This is the runnable filter surface for hand-built graphs. It derives over
    the span it was handed, so it is causal/prefix semantics; whole-series GUI
    and CSV parity use `detect_series` above until the graph migration can
    remove schema-v5 detector fields.
    """
    series = np.stack([np.asarray(frame.data, np.float32).reshape(-1) for frame in span])
    update = detect_series(
        series,
        params,
        start_index=span.start,
        workers=ALL_CORES,
    )
    gate = update.gate
    value = np.nan if gate is None else float(gate[-1])
    return Frame(
        data=np.array([[value]], dtype=np.float32),
        index=span.target.index,
        channels=ChannelSpec.GRAY,
    )


def _series2d(series: FloatArray) -> NDArray[np.float32]:
    array = np.asarray(series, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError(f"detect expects a 2D (frames, elements) series, got shape {array.shape}")
    if array.shape[0] == 0:
        raise ValueError("detect expects at least one frame")
    return array
