






















from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from sieve.core.detection import (
    count_band_to_counts,
    detect_gate,
    gate_intervals,
    inband_count,
    windowed_mean,
)
from sieve.core.detection import settled_frames as settled_after_window
from sieve.core.pipeline_model import DetectorSettings
from sieve.core.wavelet import band_indices, default_freqs, morlet_band_power
from sieve.core.wavelet import settled_frames as settled_after_coi

FloatArray = NDArray[np.floating[Any]]


@dataclass(frozen=True, slots=True)
class DetectorUpdate:








    band_power: NDArray[np.float32]
    count: NDArray[np.float32]
    windowed: NDArray[np.float32]
    gate: NDArray[np.bool_] | None
    intervals: tuple[tuple[int, int], ...] | None


    band_rows: tuple[int, int]


def detect(
    series: FloatArray,
    fps: float,
    settings: DetectorSettings,
    *,
    start_index: int = 0,
    band_power: NDArray[np.float32] | None = None,
    workers: int,
) -> DetectorUpdate:























    freqs = default_freqs(fps)
    i, j = band_indices(freqs, settings.freq_band[0], settings.freq_band[1])
    if band_power is None:
        band_power = morlet_band_power(series, fps, freqs, i, j, workers=workers)
    count = inband_count(band_power, settings.value_band[0], settings.value_band[1])
    windowed = windowed_mean(count, settings.window_frames, settings.centered)
    if settings.count_frac is None:
        gate = None
        intervals = None
    else:
        lo, hi = count_band_to_counts(
            settings.count_frac[0], settings.count_frac[1], band_power.shape[1]
        )
        gate = detect_gate(windowed, lo, hi)
        intervals = tuple(gate_intervals(gate, start=start_index))
    return DetectorUpdate(
        band_power=band_power,
        count=count,
        windowed=windowed,
        gate=gate,
        intervals=intervals,
        band_rows=(i, j),
    )


def settled_for(frames: int, fps: float, settings: DetectorSettings, *, final: bool) -> int:












    if final:
        return frames
    freqs = default_freqs(fps)
    i, j = band_indices(freqs, settings.freq_band[0], settings.freq_band[1])
    return min(
        settled_after_coi(frames, fps, freqs[i:j]),
        settled_after_window(frames, settings.window_frames, settings.centered),
    )


def gate_to(update: DetectorUpdate, settled: int, start_index: int) -> DetectorUpdate:






    gate = update.gate
    if gate is None or settled >= gate.shape[0]:
        return update
    clipped = gate[:settled]
    return DetectorUpdate(
        band_power=update.band_power,
        count=update.count,
        windowed=update.windowed,
        gate=clipped,
        intervals=tuple(gate_intervals(clipped, start=start_index)),
        band_rows=update.band_rows,
    )
