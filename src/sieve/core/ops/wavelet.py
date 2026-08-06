"""Morlet continuous wavelet transform for per-block signal series.

The temporal filter of the live tab: band power is this scalogram summed over
one frequency band. Ported from v1 (`antscihub-optical-flow-detector`,
`core/wavelet.py`) semantics-intact, because the transform *is* the feature —
the standard Torrence & Compo (1998) construction with ``w0 = 6``, normalized
so power is comparable across scales.

FFT-based via `scipy.fft` rather than `numpy.fft`: it keeps float32 inputs in
single precision (complex64, half the memory traffic) and pads to a fast
composite length (a prime T would otherwise fall back to Bluestein).

**The threading is this module's, not `scipy.fft`'s.** `morlet_band_power` used
to hand ``workers`` straight to `scipy.fft` and assume it split the batch. On
the build this ships against it does not: 1, 2, 8, 16, and 32 workers time
identically, on the strided ``axis=0`` call the transform actually makes *and*
on a fully contiguous batch — so the whole ``(T, B)`` pass ran single-threaded
while `mutual/shares.py` carefully budgeted threads for it. The block-chunk
loop is now run on a `ThreadPoolExecutor` and the inner FFTs are told
``workers=1``, which measures 4.9x at eight threads on the reference stress
workload and cannot silently become 1x again — the pool is ours.
`docs/findings/2026.07.27-scipy-fft-workers-does-nothing-here.md` has the table.

Lives in `core/` because it is numpy/scipy math with no Qt, no cv2, and no
frame contract — the tab-side detector calls it over series the pipeline
extracted, and a headless parity check calls the same functions. The CWT is
deliberately *not* a pipeline kernel this milestone: it needs the whole series
and the kernel contract is per-frame (see the parity plan, § 2, hybrid chain).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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

#: Default thread count: every core this process may use. A whole-clip pass, a
#: CLI run, and a headless parity check all want the whole machine, and `core/`
#: holds no policy about who else might want it — a caller that must leave room
#: says so, which is what `mutual/shares.py` does and the only place in the
#: tree that needs to.
ALL_CORES = -1


def _pool_size(workers: int) -> int | None:
    """`workers` as a `ThreadPoolExecutor` size; `None` is the stdlib default.

    `ALL_CORES` becomes `None` rather than `os.cpu_count()` on purpose.
    `mutual.machine.available_cpus` is importable from here now that the machine
    reading lives below this module, but taking it would still be this module holding
    a policy about how much of the machine a caller meant — and re-deriving
    "how much do I have" via `os.cpu_count` is exactly the second answer
    `resolve_workers` documents at length as the thing to avoid. The stdlib's
    own default is a third party to the disagreement rather than a party in
    it, and it is what "every core" already meant when this number went to
    `scipy.fft`.
    """
    return None if workers <= 0 else workers


# scipy.fft's stubs return `tuple[Dispatchable]` under strict pyright; these
# three wrappers are where that unknowability is contained, so the transform
# code below stays fully typed.
def _fast_len(n: int) -> int:
    return int(
        cast(int, _fft.next_fast_len(n))  # pyright: ignore[reportUnknownMemberType]
    )


def _fft_time_axis(x: FloatArray, n: int, workers: int) -> ComplexArray:
    return cast(
        ComplexArray,
        _fft.fft(x, n=n, axis=0, workers=workers),  # pyright: ignore[reportUnknownMemberType]
    )


def _ifft_time_axis(buf: ComplexArray, workers: int) -> ComplexArray:
    return cast(
        ComplexArray,
        _fft.ifft(buf, axis=0, workers=workers, overwrite_x=True),  # pyright: ignore[reportUnknownMemberType]
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


#: E-folding times of zero-padding applied before the FFT, so the record does
#: not circularly wrap onto itself.
#:
#: This was one — the e-folding time itself — and one is not the support. An
#: e-folding is a single decay constant, so at the record's end the wavelet
#: still has ~37% of its amplitude left, and `next_fast_len` was leaving a gap
#: of ~56 frames against a 0.5 Hz wavelet whose meaningful support is over
#: twice that. A strong event near one end therefore wrapped onto the other:
#: measured at **2.4% of full band-power scale** on a burst placed against the
#: cut, which is far more than enough to flip a marginally placed detection
#: gate at the opposite end of the window.
#:
#: Three, because that is where it stops mattering: the same measurement gives
#: 1.5e-5 at two and 3.0e-7 at three, and 4 and 6 sit at the same 1.7e-7 float32
#: floor. The cost is a few hundred extra samples in one FFT.
#:
#: The whole-clip path had this defect too and it was merely less visible —
#: a working window the user has positioned *on* an event is exactly the case
#: that puts strong signal against a record boundary.
PAD_EFOLDINGS = 3.0

#: E-folding times a partial record holds back before calling a frame settled.
#:
#: Two, not one, and the difference is measured rather than argued.
#: `coi_efolding_s` is a *decay scale* — its own docstring says contamination
#: decays through the wedge rather than stopping at its edge — so treating one
#: e-folding as a boundary leaves real pad leakage inside the region a caller
#: was told is final.
#:
#: Measured against a whole-record reference (and *after* `PAD_EFOLDINGS`, whose
#: wraparound otherwise swamps this): at one e-folding the worst error inside
#: the frontier sits exactly at the last settled index — the trailing pad, still
#: leaking — at ~1.5e-3 of full band-power scale. At two it falls to ~4e-5 and
#: the worst index *moves into the interior*, where it is FFT-length
#: discretization rather than the cut. Three buys nothing further. Two is
#: therefore where the frontier stops being the limiting factor.
#: `docs/findings/` carries the table.
#:
#: The cost is trailing graph: ~5.5 s at 0.5 Hz against ~2.7 s. It is charged
#: against the *band's* lowest frequency, so a detector tuned to a real
#: behavioural band pays a fraction of that — only the wide-open default band
#: pays the worst case, and only for gating, since the curve still draws.
COI_SETTLE_EFOLDINGS = 1.0


def settled_frames(n_frames: int, fs: float, freqs_hz: FloatArray) -> int:
    """How many leading frames of a *truncated* record already have their final
    power — i.e. the frontier a partial transform may be read up to.

    `morlet_power` zero-pads past the end of whatever record it is handed, so
    for a record still being filled the trailing wedge is not merely
    untrustworthy, it is *provisional*: those coefficients change when the next
    frames arrive and the pad moves. Everything before the widest e-folding
    time in `freqs_hz` is already final and will survive the record growing.

    Pass the *band's* frequencies, not the whole bank. Contamination at the cut
    comes from the daughters actually summed, so a detector tuned to a high
    band settles close to the frontier where one reaching down to 0.5 Hz needs
    seconds of it — and denominating this on the bank instead would hold back
    graph the transform had already finished with.

    The wedge is `COI_SETTLE_EFOLDINGS` e-folding times wide, not one; see that
    constant for the measurement that set it.

    A record shorter than its own COI has nothing settled, which is 0 rather
    than a negative frontier a caller would have to remember to clamp.
    """
    edge = coi_edge_samples(np.asarray(freqs_hz, np.float64), fs)
    if n_frames <= 0 or edge.size == 0:
        # An empty bank settles nothing rather than raising on `max`. Callers
        # coming through `band_indices` cannot produce one — it snaps to the
        # nearest scale rather than returning an empty span — but this is
        # public `core/` arithmetic and refusing to answer is worse than
        # answering conservatively.
        return 0
    return max(0, n_frames - int(np.ceil(float(edge.max()) * COI_SETTLE_EFOLDINGS)))


def default_freqs(fps: float, fmin: float = 0.5, fmax: float = 25.0, n: int = 24) -> FloatArray:
    """Log-spaced frequency bank, capped below Nyquist (0.45 · fps)."""
    return np.geomspace(fmin, min(fmax, 0.45 * fps), n)


def morlet_power(
    x: FloatArray, fs: float, freqs_hz: FloatArray, *, workers: int = ALL_CORES
) -> NDArray[np.float32]:
    """Morlet scalogram power. ``x`` (T,) or (T, B) → (F, T) or (F, T, B) float32.

    Loops frequencies to bound memory; each is one FFT-domain multiply plus an
    inverse FFT along the time axis. Zero-pads past the largest wavelet's
    e-folding support so the ends see zeros instead of circularly wrapping
    onto the other end of the record, then rounds up to a fast composite
    length.

    ``workers`` is passed to `scipy.fft` and defaults to every core, which is
    what a batch or headless caller should have. An interactive caller sharing
    the machine with decode threads passes a cap; see `mutual/shares.py`. It
    changes only how fast the answer arrives, never the answer.
    """
    x32 = np.asarray(x, np.float32)
    squeeze = x32.ndim == 1
    if squeeze:
        x32 = x32[:, None]
    n_frames = x32.shape[0]
    dt = 1.0 / fs
    scales = morlet_scales(freqs_hz)
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt * PAD_EFOLDINGS))
    n = _fast_len(n_frames + support)
    xf = _fft_time_axis(x32, n, workers)  # complex64
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    heavi = omega > 0
    out = np.empty((len(scales), *x32.shape), np.float32)
    buf = np.empty_like(xf)  # reused scratch: xf * daughter
    for i, s in enumerate(scales):
        np.multiply(xf, _daughter(float(s), omega, heavi, dt)[:, None], out=buf)
        w = _ifft_time_axis(buf, workers)[:n_frames]
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
    *,
    workers: int = ALL_CORES,
) -> NDArray[np.float32]:
    """Scalogram power summed over frequency rows ``[i, j)``. ``x`` (T,) or
    (T, B) → (T,) or (T, B) float32.

    Numerically identical to ``morlet_power(x, fs, freqs_hz)[i:j].sum(axis=0)``
    but never materializes the full (F, T, B) cube: it derives the zero-pad
    length from the *whole* bank's largest scale (so the band sum matches a
    full-cube slice exactly — the property the test pins), yet transforms only
    the band's scales, chunked over block columns so a whole-clip pass stays
    memory-bounded.

    ``workers`` is how many block chunks are transformed at once, defaulting to
    every core unless the caller has someone to leave room for. See the module
    docstring for why the pool is here rather than `scipy.fft`'s.

    **The pool cannot move a bit.** Chunks write disjoint column slices of one
    preallocated output and share nothing but read-only inputs, and the summation
    order *within* a chunk — the only place floats are added — is the serial
    order untouched. So the thread count is a wall-clock choice and never an
    answer, which is what `test_the_thread_count_cannot_move_a_bit` pins and what
    lets an interactive pass and a headless one be compared at all.
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
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt * PAD_EFOLDINGS))
    n = _fast_len(n_frames + support)
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    heavi = omega > 0
    daughters = [_daughter(float(s), omega, heavi, dt) for s in band]
    out = np.zeros((n_frames, n_blocks), np.float32)
    chunk = max(1, block_chunk)
    starts = tuple(range(0, n_blocks, chunk))

    def transform(c0: int) -> None:
        """One chunk of columns, start to finish. Every buffer is a local, so
        two chunks running at once cannot meet in a scratch array."""
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
        # No pool for the cases that cannot use one: a caller that asked for one
        # thread meant it, and a single chunk has nothing to overlap with. Both
        # are the ordinary shape in tests and in the 1-D `squeeze` path, where
        # spinning up an executor would be most of the cost.
        for c0 in starts:
            transform(c0)
    else:
        with ThreadPoolExecutor(max_workers=_pool_size(workers)) as pool:
            # Consumed rather than left lazy: `map` defers exceptions to
            # iteration, and a chunk that raised into an unread iterator would
            # leave `out` holding zeros for those columns — blocks reading as
            # silent rather than as failed, which is rule 6 exactly.
            for _ in pool.map(transform, starts):
                pass
    return out[:, 0] if squeeze else out
