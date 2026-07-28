"""Bands, threshold, and window composed into intervals. Qt-free, front-end-free.

`core/wavelet.py` holds the transform and `core/detection.py` the gate; this is
the composition of them that a saved `DetectorSettings` names, and the only
thing between a document on disk and the intervals it claims.

**Two frontiers, and the smaller wins.** A record still being filled is
provisional at its cut in two independent ways: the transform zero-pads past
the end, so the trailing cone of influence is not settled
(`core.wavelet.settled_frames`), and a centered detection window near the cut
averages frames that have not arrived (`core.detection.settled_frames`).
`settled_for` is where they meet and `gate_to` is what enforces it — curves are
published in full and drawn faded past the frontier, because a provisional
*value* reads as one, while a provisional *detection* does not: an interval
that appears and then vanishes as the record grows is a worse lie than a graph
that has not got there yet.

**Unset count threshold means disarmed, not unbounded.** `count_frac` is
`None` until a user places the handle, and this module then produces no gate
and no intervals — not empty ones, which would be "armed and found nothing".
v1's unset-means-unbounded painted a fresh tab as one giant detection.
"""

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
    """One pure derivation over one collected series.

    `band_power` is retained so value-band / threshold / D re-tunes are the
    cheap tier (no transform); a frequency-band or upstream change discards
    it and recomputes. `gate` and `intervals` are None when disarmed — not
    empty, which would be "armed and found nothing".
    """

    band_power: NDArray[np.float32]  # (T, B)
    count: NDArray[np.float32]  # (T,)
    windowed: NDArray[np.float32]  # (T,)
    gate: NDArray[np.bool_] | None
    intervals: tuple[tuple[int, int], ...] | None
    #: The snapped bank rows the transform actually used — what the
    #: scalogram title renders (the title tells the truth the transform uses).
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
    """The whole derivation `DetectorSettings` names, over one series.

    `series` is the collected `(T, B)` block-signal columns. Pass the previous
    update's `band_power` when only the value band, threshold, D, or centered
    changed — the cheap tier — and leave it None when the frequency band or
    anything upstream moved.

    `start_index` is the series' first source frame, so intervals come back in
    absolute frames (what the seeker's ticks jump to).

    `workers` caps the transform's threads and is **required, with no default**.
    It had one — `ALL_CORES` — and `gui/filter_tab.py` inherited it by omission,
    running a full Morlet transform over every core on the GUI thread beside two
    decode pools. That is the fourth consumer `gui/concurrency.py` exists to
    forbid, and `tests/unit/test_concurrency.py` could not see it: a test that
    sums declared constants checks the declaration, not the calls. Deleting the
    default moves enforcement to pyright, which checks every call site.

    A headless caller wanting the whole machine passes `ALL_CORES` and says so.
    Anything running beside the interactive pools passes
    `concurrency.DETECTOR_WORKERS`.
    """
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
    """Where a record of `frames` stops being provisional, under `settings`.

    A final pass claims the whole record — a render that is over has no moving
    frontier, and its edges mean what the clip's edges mean. Which is why a
    headless whole-clip run never needs the arithmetic below and an interactive
    partial always does.

    Shared rather than living inside `detect`, because a D drag over a partial
    series *moves* this frontier: widening a centered window pulls it back, and
    a caller that kept the frontier its last full pass reported would go on
    painting a gate over frames the wider window no longer settles.
    """
    if final:
        return frames
    freqs = default_freqs(fps)
    i, j = band_indices(freqs, settings.freq_band[0], settings.freq_band[1])
    return min(
        settled_after_coi(frames, fps, freqs[i:j]),
        settled_after_window(frames, settings.window_frames, settings.centered),
    )


def gate_to(update: DetectorUpdate, settled: int, start_index: int) -> DetectorUpdate:
    """Truncate the gate and its intervals to the settled frontier.

    The curves are left whole — see the module docstring on why a provisional
    value and a provisional detection are not the same claim. The summary's
    count only ever grows.
    """
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
