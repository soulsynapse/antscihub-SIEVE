from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from scipy import fft as _fft


W0 = 6.0

FloatArray = NDArray[np.floating[Any]]
ComplexArray = NDArray[np.complexfloating[Any, Any]]


ALL_CORES = -1


def _pool_size(workers: int) -> int | None:
    return None if workers <= 0 else workers


def _fast_len(n: int) -> int:
    return int(cast(int, _fft.next_fast_len(n)))


def _fft_time_axis(x: FloatArray, n: int, workers: int) -> ComplexArray:
    return cast(
        ComplexArray,
        _fft.fft(x, n=n, axis=0, workers=workers),
    )


def _ifft_time_axis(buf: ComplexArray, workers: int) -> ComplexArray:
    return cast(
        ComplexArray,
        _fft.ifft(buf, axis=0, workers=workers, overwrite_x=True),
    )


def morlet_scales(freqs_hz: FloatArray) -> FloatArray:
    f = np.asarray(freqs_hz, np.float64)
    return (W0 + np.sqrt(2.0 + W0 * W0)) / (4.0 * np.pi * f)


def coi_efolding_s(freqs_hz: FloatArray) -> FloatArray:
    return np.sqrt(2.0) * morlet_scales(freqs_hz)


def coi_edge_samples(freqs_hz: FloatArray, fs: float) -> FloatArray:
    return coi_efolding_s(freqs_hz) * float(fs)


PAD_EFOLDINGS = 3.0


COI_SETTLE_EFOLDINGS = 2.0


def settled_frames(n_frames: int, fs: float, freqs_hz: FloatArray) -> int:
    edge = coi_edge_samples(np.asarray(freqs_hz, np.float64), fs)
    if n_frames <= 0 or edge.size == 0:
        return 0
    return max(0, n_frames - int(np.ceil(float(edge.max()) * COI_SETTLE_EFOLDINGS)))


def default_freqs(
    fps: float, fmin: float = 0.5, fmax: float = 25.0, n: int = 24
) -> FloatArray:
    return np.geomspace(fmin, min(fmax, 0.45 * fps), n)


def morlet_power(
    x: FloatArray, fs: float, freqs_hz: FloatArray, *, workers: int = ALL_CORES
) -> NDArray[np.float32]:
    x32 = np.asarray(x, np.float32)
    squeeze = x32.ndim == 1
    if squeeze:
        x32 = x32[:, None]
    n_frames = x32.shape[0]
    dt = 1.0 / fs
    scales = morlet_scales(freqs_hz)
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt * PAD_EFOLDINGS))
    n = _fast_len(n_frames + support)
    xf = _fft_time_axis(x32, n, workers)
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    heavi = omega > 0
    out = np.empty((len(scales), *x32.shape), np.float32)
    buf = np.empty_like(xf)
    for i, s in enumerate(scales):
        np.multiply(xf, _daughter(float(s), omega, heavi, dt)[:, None], out=buf)
        w = _ifft_time_axis(buf, workers)[:n_frames]
        out[i] = w.real**2 + w.imag**2
    return out[:, :, 0] if squeeze else out


def _daughter(
    scale: float, omega: FloatArray, heavi: NDArray[np.bool_], dt: float
) -> NDArray[np.complex64]:
    norm = np.sqrt(2.0 * np.pi * scale / dt) * np.pi**-0.25
    return (norm * heavi * np.exp(-0.5 * (scale * omega - W0) ** 2)).astype(
        np.complex64
    )


def band_indices(freqs_hz: FloatArray, flo: float, fhi: float) -> tuple[int, int]:
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
    *,
    workers: int = ALL_CORES,
) -> NDArray[np.float32]:
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
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt * PAD_EFOLDINGS))
    n = _fast_len(n_frames + support)
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    heavi = omega > 0
    daughters = [_daughter(float(s), omega, heavi, dt) for s in band]
    out = np.zeros((n_frames, n_blocks), np.float32)
    chunk = max(1, block_chunk)
    starts = tuple(range(0, n_blocks, chunk))
    def transform(c0: int) -> None:
        c1 = min(n_blocks, c0 + chunk)
        xf = _fft_time_axis(x32[:, c0:c1], n, 1)
        acc = np.zeros((n_frames, c1 - c0), np.float32)
        buf = np.empty_like(xf)
        for d in daughters:
            np.multiply(xf, d[:, None], out=buf)
            w = _ifft_time_axis(buf, 1)[:n_frames]
            acc += w.real**2 + w.imag**2
        out[:, c0:c1] = acc
    if workers == 1 or len(starts) < 2:
        for c0 in starts:
            transform(c0)
    else:
        with ThreadPoolExecutor(max_workers=_pool_size(workers)) as pool:
            for _ in pool.map(transform, starts):
                pass
    return out[:, 0] if squeeze else out
