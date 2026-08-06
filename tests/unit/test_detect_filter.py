"""The detector's filter surface: registered params, warmup, and gate channel."""

from __future__ import annotations

import math

import numpy as np
import pytest

from sieve.core.filter_base import ElementKind, ElementNames, Mode, node_warmup_frames
from sieve.core.ops.wavelet import default_freqs
from sieve.core.pipeline_model import DetectorSettings
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.detect.detector import detect
from sieve.filters import discover
from sieve.filters.detect import DetectParams, detect_cpu, detect_series, pooled_scalogram

FPS = 20.0


def _span(series: np.ndarray, *, start: int = 100) -> FrameSpan:
    return FrameSpan(
        tuple(
            Frame(data=row.astype(np.float32), index=start + offset, channels=ChannelSpec.GRAY)
            for offset, row in enumerate(series)
        )
    )


def test_detect_is_a_discovered_windowed_filter_with_owned_params() -> None:
    spec = next(spec for spec in discover() if spec.filter_id == "detect")

    assert spec.params_model is DetectParams
    assert spec.mode is Mode.WINDOWED
    assert spec.element is ElementKind.FRAME
    assert spec.element_names == ElementNames("frame", "frames")
    assert spec.primary_params == ("freq_band", "value_band", "count_frac", "window_frames")


def test_detector_settings_bridge_into_hashable_filter_params() -> None:
    settings = DetectorSettings(
        value_band=(5.0, math.inf),
        count_frac=(0.25, math.inf),
        window_frames=5,
        centered=False,
    )

    params = DetectParams.from_settings(settings, fps=FPS)

    assert params.to_settings() == settings
    assert params.canonical_json() == (
        '{"centered":false,"count_frac":[0.25,Infinity],"fps":20.0,'
        '"freq_band":[0.0,Infinity],"value_band":[5.0,Infinity],"window_frames":5}'
    )
    assert node_warmup_frames((DetectParams.spec(), params)) == params.warmup_frames()


def test_detect_warmup_bound_is_derived_from_the_params_model() -> None:
    spec = DetectParams.spec()
    corner = DetectParams(fps=240.0, freq_band=(0.0, math.inf), window_frames=600)

    assert spec.warmup_frames == corner.warmup_frames()
    assert spec.warmup_frames >= FrameCount(599)
    assert spec.settling_epsilon == 0.0


def test_series_adapter_preserves_the_whole_record_detector_semantics() -> None:
    """The GUI/CSV flip reaches the filter boundary without moving the numbers."""
    series = np.zeros((80, 6), np.float32)
    series[30:55] = 10.0
    params = DetectParams(
        fps=FPS,
        value_band=(5.0, math.inf),
        count_frac=(0.5, math.inf),
        window_frames=5,
        centered=True,
    )

    update = detect_series(series, params, start_index=100, workers=1)
    expected = detect(series, FPS, params.to_settings(), start_index=100, workers=1)

    assert np.array_equal(update.band_power, expected.band_power)
    assert np.array_equal(update.count, expected.count)
    assert np.array_equal(update.windowed, expected.windowed)
    assert update.gate is not None and expected.gate is not None
    assert np.array_equal(update.gate, expected.gate)
    assert update.intervals == expected.intervals


def test_series_adapter_rejects_a_grid_that_was_not_flattened() -> None:
    """The compatibility surface takes a collected `(T, B)` series, not frames."""
    params = DetectParams(fps=FPS)

    with pytest.raises(ValueError, match=r"2D \(frames, elements\) series"):
        detect_series(np.zeros((4, 2, 3), np.float32), params, workers=1)


def test_pooled_scalogram_is_filter_side_work_for_the_gui_plot() -> None:
    series = np.ones((30, 5), np.float32)
    params = DetectParams(fps=FPS)

    pooled = pooled_scalogram(series, params, workers=1)

    assert pooled.shape == (default_freqs(FPS).shape[0], series.shape[0])
    assert pooled.dtype == np.float32


def test_detect_kernel_emits_the_same_target_gate_as_the_series_derivation() -> None:
    series = np.zeros((80, 6), np.float32)
    series[30:55] = 10.0
    params = DetectParams(
        fps=FPS,
        value_band=(5.0, math.inf),
        count_frac=(0.5, math.inf),
        window_frames=5,
        centered=False,
    )

    frame = detect_cpu(_span(series), params)
    expected = detect(series, FPS, params.to_settings(), start_index=100, workers=1)

    assert frame.index == 179
    assert frame.channels is ChannelSpec.GRAY
    assert frame.data.shape == (1, 1)
    assert frame.data.dtype == np.float32
    assert expected.gate is not None
    assert frame.data[0, 0] == np.float32(expected.gate[-1])


def test_disarmed_detection_is_absent_not_false() -> None:
    series = np.ones((12, 4), np.float32)

    frame = detect_cpu(_span(series), DetectParams(fps=FPS, count_frac=None))

    assert np.isnan(frame.data[0, 0])


def test_filter_params_keep_the_detector_bounds_ordered() -> None:
    with pytest.raises(ValueError, match="value_band must be ordered"):
        DetectParams(value_band=(2.0, 1.0))
