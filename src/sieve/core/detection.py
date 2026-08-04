"""The detection chain as pure functions: count → windowed mean → gate.

Ported from v1 (`antscihub-optical-flow-detector`, `core/detection.py`), where
these formulas were shared verbatim between the live preview and the
whole-video pass — the property that made a detection found over the whole
clip reproduce when its window was re-opened. That sharing is the best part of
v1 and is kept: the live tab, a future whole-video pass, and the parity check
all call these, and none of them re-implements a comparison.

Two deliberate deviations from v1, both settled in the parity plan:

* **The count threshold is denominated as a fraction of the region's blocks**,
  converted to counts in exactly one place (`count_band_to_counts`). v1 stored
  raw counts and carried them across grid changes with a re-denomination
  helper (`rescale_count_band`) that every caller had to remember — a measured
  13x foot-gun. A fraction survives a block-size change by meaning the same
  thing.
* **There is no three-valued band encoding.** v1 threaded `None`/±inf/float
  through every consumer; here "unset means disarmed" is the *tab's* state
  (it simply does not call `detect_gate`), and these functions take floats,
  with ``inf`` legal where "unbounded" is a value a handle can express.

Two distinct bands meet here and are easy to conflate: the *value band* is
applied to per-block band power by `inband_count`; the *frequency band* was
already applied upstream by `wavelet.morlet_band_power`'s summation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.floating[Any]]


def inband_count(m: FloatArray, lo: float, hi: float) -> NDArray[np.float32]:
    """# blocks whose band power lies in ``[lo, hi]`` per frame. ``m`` is (T, B).

    Non-finite block values never count, whatever the band: a NaN from a
    degenerate block must not become a detection by comparing true against
    ``-inf``.
    """
    arr = np.asarray(m)
    inband = (arr >= lo) & (arr <= hi) & np.isfinite(arr)
    return inband.sum(axis=1).astype(np.float32)


def window_bounds(
    n_frames: int, window: int, centered: bool
) -> tuple[NDArray[np.intp], NDArray[np.intp], NDArray[np.float32]]:
    """Per-frame prefix-sum bounds ``(hi, lo, effective_length)`` for a
    detection window of ``window`` frames.

    Centered is ``[t - W//2, t + (W - W//2))``, trailing is ``[t - W + 1, t]``.
    Windows truncate at the clip edges and the returned effective length is
    the *true* number of frames in each window — dividing by it is what keeps
    the means honest there, rather than diluting edge frames against zeros
    that were never observed.
    """
    t = np.arange(n_frames)
    if centered:
        lo = np.maximum(0, t - window // 2)
        hi = np.minimum(n_frames, t + (window - window // 2))
    else:
        hi = t + 1
        lo = np.maximum(0, hi - window)
    return hi, lo, (hi - lo).astype(np.float32)


def windowed_mean(count: FloatArray, window: int, centered: bool) -> NDArray[np.float32]:
    """Centered/trailing mean of a per-frame series over ``window`` frames.

    The reason D exists: a 1-frame spike of N blocks dilutes to N/W and cannot
    fake a sustained event. Prefix-sum, so the cost is O(T) regardless of W —
    this is on the cheap re-derive tier that runs on every threshold drag.
    ``window`` is in *frames*; the caller labels it in seconds.
    """
    c32 = np.asarray(count, np.float32)
    n_frames = c32.shape[0]
    if n_frames == 0 or window <= 1:
        return c32.astype(np.float32)
    c = np.concatenate([[0.0], np.cumsum(c32, dtype=np.float64)])
    hi, lo, neff = window_bounds(n_frames, window, centered)
    return ((c[hi] - c[lo]) / neff).astype(np.float32)


def settled_frames(n_frames: int, window: int, centered: bool) -> int:
    """How many leading frames of a *truncated* series already have their final
    windowed mean — the second frontier, after `wavelet.settled_frames`.

    `window_bounds` clamps `hi` to the record's length and divides by the true
    count, which is exactly right at the *clip's* end and wrong at a frontier
    that is still moving: a centered window near the cut averages fewer frames
    than it asked for and reports a value that changes when the rest arrive. So
    a centered window settles `window - window // 2 - 1` frames back, and a
    trailing window — which never reads forward — settles everywhere.

    This is about a record still being filled. A caller that has the whole
    window in hand must not apply it: there the truncation is the clip, and the
    edge means what it says.
    """
    if n_frames <= 0:
        return 0
    if not centered or window <= 1:
        return n_frames
    return max(0, n_frames - (window - window // 2) + 1)


def count_band_to_counts(frac_lo: float, frac_hi: float, region_blocks: int) -> tuple[float, float]:
    """The one place a fractional count band becomes block counts.

    ``frac_lo``/``frac_hi`` are fractions of ``region_blocks`` (the number of
    blocks the detector's region holds — the denominator of every count it
    produces). Infinite endpoints pass through: "unbounded above" is not a
    fraction and does not denominate. Zero survives the multiply unchanged,
    which is correct — "at least none" is grid-independent.
    """
    if region_blocks < 0:
        raise ValueError(f"region_blocks must be non-negative, got {region_blocks}")

    def conv(v: float) -> float:
        return v * region_blocks if np.isfinite(v) else v

    return conv(frac_lo), conv(frac_hi)


def detect_gate(windowed: FloatArray, lo: float, hi: float) -> NDArray[np.bool_]:
    """Positive detection per frame: windowed in-band count within ``[lo, hi]``.

    ``lo``/``hi`` are in *counts* — the caller converts a stored fraction via
    `count_band_to_counts` first. Boolean rather than v1's float 0/1: the gate
    is a predicate and every consumer was comparing against 0.5 to recover the
    bool.
    """
    w = np.asarray(windowed)
    return (w >= lo) & (w <= hi)


def gate_intervals(gate: NDArray[np.bool_], start: int = 0) -> list[tuple[int, int]]:
    """Contiguous ``[start, end)`` frame runs where the gate is on.

    ``start`` is added to both endpoints, so a gate computed over a working
    window reports absolute source-frame intervals — the form the seeker's
    ticks and the prev/next jumps consume.
    """
    g = np.asarray(gate, bool)
    if not g.any():
        return []
    edges = np.diff(np.concatenate([[0], g.astype(np.int8), [0]]))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return [(int(s + start), int(e + start)) for s, e in zip(starts, ends, strict=True)]
