"""Morlet continuous wavelet transform for per-block signal series.

The temporal filter of the live tab: band power is this scalogram summed over
one frequency band. Ported from v1 (`antscihub-optical-flow-detector`,
`core/wavelet.py`) semantics-intact, because the transform *is* the feature —
the standard Torrence & Compo (1998) construction with ``w0 = 6``, normalized
so power is comparable across scales.

FFT-based via `scipy.fft` rather than `numpy.fft`: it keeps float32 inputs in
single precision (complex64, half the memory traffic), pads to a fast
composite length (a prime T would otherwise fall back to Bluestein), and
threads across block columns (``workers=-1``). v1 measured ~10x on the
per-block ``(T, B)`` workload from exactly these three properties.

Lives in `core/` because it is numpy/scipy math with no Qt, no cv2, and no
frame contract — the tab-side detector calls it over series the pipeline
extracted, and a headless parity check calls the same functions. The CWT is
deliberately *not* a pipeline kernel this milestone: it needs the whole series
and the kernel contract is per-frame (see the parity plan, § 2, hybrid chain).
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from scipy import fft as _fft  # pyright: ignore[reportMissingTypeStubs]

#: Morlet nondimensional frequency. A constant rather than a parameter: every
#: scale, COI width, and bank below is derived from it, and two series
#: transformed under different ``W0`` are not comparable.
W0 = 6.0

FloatArray = NDArray[np.floating[Any]]
ComplexArray = NDArray[np.complexfloating[Any, Any]]


# scipy.fft's stubs return `tuple[Dispatchable]` under strict pyright; these
# three wrappers are where that unknowability is contained, so the transform
# code below stays fully typed.
def _fast_len(n: int) -> int:
    return int(
        cast(int, _fft.next_fast_len(n))  # pyright: ignore[reportUnknownMemberType]
    )


def _fft_time_axis(x: FloatArray, n: int) -> ComplexArray:
    return cast(
        ComplexArray,
        _fft.fft(x, n=n, axis=0, workers=-1),  # pyright: ignore[reportUnknownMemberType]
    )


def _ifft_time_axis(buf: ComplexArray) -> ComplexArray:
    return cast(
        ComplexArray,
        _fft.ifft(buf, axis=0, workers=-1, overwrite_x=True),  # pyright: ignore[reportUnknownMemberType]
    )


def morlet_scales(freqs_hz: FloatArray) -> FloatArray:
    """Wavelet scale ``s`` for each desired Fourier frequency (w0=6 Morlet)."""
    f = np.asarray(freqs_hz, np.float64)
    return (W0 + np.sqrt(2.0 + W0 * W0)) / (4.0 * np.pi * f)


def coi_efolding_s(freqs_hz: FloatArray) -> FloatArray:
    """Cone-of-influence half-width in *seconds* for each Fourier frequency.

    Torrence & Compo's e-folding time for Morlet, ``tau = sqrt(2) * s``. Within
    ``tau`` of either end of the record the coefficients are contaminated by
    the zero-padding `morlet_power` applies rather than by the signal, so that
    wedge is artifact and must not be read as data.

    Derived from `morlet_scales` rather than baked in, so it follows ``W0`` if
    that ever moves. At w0=6 it works out to ~1.369/f seconds — ~2.74 s at
    0.5 Hz against ~0.068 s at 20 Hz.

    This is a *scale*, not a threshold: contamination decays through the wedge
    rather than stopping at its edge. A renderer should grade it (the
    scalogram plot's alpha fade), and any chunked evaluation must widen its
    chunks by it or seams ring.
    """
    return np.sqrt(2.0) * morlet_scales(freqs_hz)


def coi_edge_samples(freqs_hz: FloatArray, fs: float) -> FloatArray:
    """`coi_efolding_s` in samples at rate ``fs`` — the form a plot with a
    time axis in frames needs."""
    return coi_efolding_s(freqs_hz) * float(fs)


def default_freqs(fps: float, fmin: float = 0.5, fmax: float = 25.0, n: int = 24) -> FloatArray:
    """Log-spaced frequency bank, capped below Nyquist (0.45 · fps)."""
    return np.geomspace(fmin, min(fmax, 0.45 * fps), n)


def morlet_power(x: FloatArray, fs: float, freqs_hz: FloatArray) -> NDArray[np.float32]:
    """Morlet scalogram power. ``x`` (T,) or (T, B) → (F, T) or (F, T, B) float32.

    Loops frequencies to bound memory; each is one FFT-domain multiply plus an
    inverse FFT along the time axis. Zero-pads past the largest wavelet's
    e-folding support so the ends see zeros instead of circularly wrapping
    onto the other end of the record, then rounds up to a fast composite
    length.
    """
    x32 = np.asarray(x, np.float32)
    squeeze = x32.ndim == 1
    if squeeze:
        x32 = x32[:, None]
    n_frames = x32.shape[0]
    dt = 1.0 / fs
    scales = morlet_scales(freqs_hz)
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt))
    n = _fast_len(n_frames + support)
    xf = _fft_time_axis(x32, n)  # complex64
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    heavi = omega > 0
    out = np.empty((len(scales), *x32.shape), np.float32)
    buf = np.empty_like(xf)  # reused scratch: xf * daughter
    for i, s in enumerate(scales):
        np.multiply(xf, _daughter(float(s), omega, heavi, dt)[:, None], out=buf)
        w = _ifft_time_axis(buf)[:n_frames]
        out[i] = w.real**2 + w.imag**2
    return out[:, :, 0] if squeeze else out


def _daughter(
    scale: float, omega: FloatArray, heavi: NDArray[np.bool_], dt: float
) -> NDArray[np.complex64]:
    """One scale's frequency-domain Morlet daughter, T&C-normalized."""
    norm = np.sqrt(2.0 * np.pi * scale / dt) * np.pi**-0.25
    return (norm * heavi * np.exp(-0.5 * (scale * omega - W0) ** 2)).astype(np.complex64)


def band_indices(freqs_hz: FloatArray, flo: float, fhi: float) -> tuple[int, int]:
    """Frequency rows ``[i, j)`` covering ``[flo, fhi]`` Hz on a sorted bank.

    An empty span snaps to the single nearest scale rather than raising or
    returning nothing: the band handles are continuous and the bank is
    discrete, so a user can legitimately place both handles between the same
    two rows, and a detector with zero scales in its band is a detector that
    silently went dead. The scalogram title renders the *snapped* band for the
    same reason — the title tells the truth the transform uses.
    """
    freqs = np.asarray(freqs_hz, np.float64)
    i = int(np.searchsorted(freqs, flo, "left"))
    j = int(np.searchsorted(freqs, fhi, "right"))
    if j <= i:
        i = int(np.argmin(np.abs(freqs - flo)))
        j = i + 1
    return i, j


def morlet_band_power(
    x: FloatArray,
    fs: float,
    freqs_hz: FloatArray,
    i: int,
    j: int,
    block_chunk: int = 512,
) -> NDArray[np.float32]:
    """Scalogram power summed over frequency rows ``[i, j)``. ``x`` (T,) or
    (T, B) → (T,) or (T, B) float32.

    Numerically identical to ``morlet_power(x, fs, freqs_hz)[i:j].sum(axis=0)``
    but never materializes the full (F, T, B) cube: it derives the zero-pad
    length from the *whole* bank's largest scale (so the band sum matches a
    full-cube slice exactly — the property the test pins), yet transforms only
    the band's scales, chunked over block columns so a whole-clip pass stays
    memory-bounded.
    """
    x32 = np.asarray(x, np.float32)
    squeeze = x32.ndim == 1
    if squeeze:
        x32 = x32[:, None]
    n_frames, n_blocks = x32.shape
    dt = 1.0 / fs
    scales_all = morlet_scales(freqs_hz)
    band = scales_all[i:j]
    if band.size == 0:
        k = int(np.clip(i, 0, len(scales_all) - 1))
        band = scales_all[k : k + 1]
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt))
    n = _fast_len(n_frames + support)
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    heavi = omega > 0
    daughters = [_daughter(float(s), omega, heavi, dt) for s in band]
    out = np.zeros((n_frames, n_blocks), np.float32)
    chunk = max(1, block_chunk)
    for c0 in range(0, n_blocks, chunk):
        c1 = min(n_blocks, c0 + chunk)
        xf = _fft_time_axis(x32[:, c0:c1], n)
        acc = np.zeros((n_frames, c1 - c0), np.float32)
        buf = np.empty_like(xf)
        for d in daughters:
            np.multiply(xf, d[:, None], out=buf)
            w = _ifft_time_axis(buf)[:n_frames]
            acc += w.real**2 + w.imag**2
        out[:, c0:c1] = acc
    return out[:, 0] if squeeze else out
