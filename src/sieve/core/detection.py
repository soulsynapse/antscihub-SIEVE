from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.floating[Any]]


def inband_count(m: FloatArray, lo: float, hi: float) -> NDArray[np.float32]:
    arr = np.asarray(m)
    inband = (arr >= lo) & (arr <= hi) & np.isfinite(arr)
    return inband.sum(axis=1).astype(np.float32)


def window_bounds(
    n_frames: int, window: int, centered: bool
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.float32]]:
    t = np.arange(n_frames)
    if centered:
        lo = np.maximum(0, t - window // 2)
        hi = np.minimum(n_frames, t + (window - window // 2))
    else:
        hi = t + 1
        lo = np.maximum(0, hi - window)
    return hi, lo, (hi - lo).astype(np.float32)


def windowed_mean(
    count: FloatArray, window: int, centered: bool
) -> NDArray[np.float32]:
    c32 = np.asarray(count, np.float32)
    n_frames = c32.shape[0]
    if n_frames == 0 or window <= 1:
        return c32.astype(np.float32)
    c = np.concatenate([[0.0], np.cumsum(c32, dtype=np.float64)])
    hi, lo, neff = window_bounds(n_frames, window, centered)
    return ((c[hi] - c[lo]) / neff).astype(np.float32)


def settled_frames(n_frames: int, window: int, centered: bool) -> int:
    if n_frames <= 0:
        return 0
    if not centered or window <= 1:
        return n_frames
    return max(0, n_frames - (window - window // 2) + 1)


def count_band_to_counts(
    frac_lo: float, frac_hi: float, region_blocks: int
) -> tuple[float, float]:
    if region_blocks < 0:
        raise ValueError(f"region_blocks must be non-negative, got {region_blocks}")
    def conv(v: float) -> float:
        return v * region_blocks if np.isfinite(v) else v
    return conv(frac_lo), conv(frac_hi)


def detect_gate(windowed: FloatArray, lo: float, hi: float) -> NDArray[np.bool_]:
    w = np.asarray(windowed)
    return (w >= lo) & (w <= hi)


def gate_intervals(gate: NDArray[np.bool_], start: int = 0) -> list[tuple[int, int]]:
    g = np.asarray(gate, bool)
    if not g.any():
        return []
    edges = np.diff(np.concatenate([[0], g.astype(np.int8), [0]]))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return [(int(s + start), int(e + start)) for s, e in zip(starts, ends, strict=True)]
