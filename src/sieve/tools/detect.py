"""Morlet band power, an in-band block count, and a centred detection gate.

The last tool of Phase 4 and the one the contract was widened for. What it
claims is that a stretch of footage holds the behaviour: per block, how much
power sits in a frequency band; per frame, how many blocks sit in a value band;
and over a window centred on the frame, whether that count sustained itself
long enough to be an event rather than a twitch.

**Three files of v2 land here, and the package between them does not.** The
transform was `core/ops/wavelet.py`, the chain was `core/ops/detection.py`, and
the composition of the two was the `detect/` package that a saved document's
detector settings named. v3 has one module, because the census that argued for
`ops/` found ten callers of which six were GUI modules computing — and all ten
collapse into this file once the preview is the pipeline and the detector is a
node (`adr/ops-admission-is-two-tools.md`, `adr/detector-is-a-node.md`). The
math is v2's line for line, including every constant it measured.

**The window is centred, and that is the whole reason this tool could not
exist in v2.** v2's contract could say only how much history a node needed, so
the runnable detector it shipped was trailing — a shape whose output at a
frame is not what the user tuned against, since every band, threshold and
window in every session was placed while looking at a two-sided result over the
whole record. The centred half arrived as `lookahead_frames`
(`core/tool_base.py`), so the parity target here is v2's `detect/` package
output and never its trailing kernel: matching that would certify the artifact
this plan replaced.

**Two frontiers became one declaration.** A record still being filled was
provisional at its cut in two independent ways — the transform zero-pads past
the end, so the trailing cone of influence is not settled, and a centred
detection window near the cut averages frames that have not arrived. v2 had a
pair of `settled_frames` functions and a `gate_to` that truncated a published
gate to the smaller of them. None of that comes over: the executor does not
emit a frame until it has read the frames this tool's declared lookahead
reaches, so every value that leaves here was computed from a full window and
there is no provisional half to fence off. The frontier is `lookahead_frames`,
and it is enforced by the loop rather than by a caller remembering to ask.

**The emitted product is the gate, one float32 per frame** — `1` detected, `0`
not, `NaN` disarmed. Unset means disarmed rather than unbounded: v1 read a
count threshold nobody had placed as "everything passes" and painted a fresh
session as one giant detection. The intervals a gate implies are rows, not
frames, and they arrive with the table emitter in Phase 5; `gate_intervals` is
here because the chain's ported cases are the spec for it.

**What the transform is.** The standard Torrence & Compo (1998) Morlet
construction at `w0 = 6`, normalized so power is comparable across scales,
carried from v1 semantics-intact because the transform *is* the feature. It
runs on `scipy.fft`: float32 in stays single precision, and `next_fast_len`
keeps a prime frame count off Bluestein's path. The threading is this module's
rather than `scipy.fft`'s — see `morlet_band_power`, and v2's
`docs/findings/2026.07.27-scipy-fft-workers-does-nothing-here.md` for the table
that made that necessary.

**Two distinct bands meet here and are easy to conflate.** The *value* band is
applied to per-block band power by `inband_count`; the *frequency* band was
already applied by `morlet_band_power`'s summation over bank rows.
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Self, cast

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, model_validator
from scipy import fft as _fft

from sieve.core.tool_base import (
    ArraySpec,
    AxisRelation,
    CaptionPart,
    DisplaySurface,
    ElementKind,
    ElementNames,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
    RowAxis,
    ValueAxis,
    WarmupKind,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.mutual.shares import DETECTOR_WORKERS

#: Morlet nondimensional frequency. A constant rather than a parameter: every
#: scale, COI width, and bank below is derived from it, and two series
#: transformed under different ``W0`` are not comparable.
W0 = 6.0

#: Default thread count: every core this process may use. A whole-record pass
#: and a headless parity check both want the whole machine, and the arithmetic
#: here holds no policy about who else might want it — a caller that must leave
#: room says so, which is what `mutual/shares.py` does and the only place in the
#: tree that needs to.
ALL_CORES = -1

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
PAD_EFOLDINGS = 3.0

#: The longest detection window a user may place, in frames.
MAX_WINDOW_FRAMES = 600

#: The highest frame rate a window or a bank may be denominated against.
#: `temporal_baseline`'s number, deliberately the same one.
MAX_FPS = 240.0

FloatArray = NDArray[np.floating[Any]]
ComplexArray = NDArray[np.complexfloating[Any, Any]]

#: What this tool is for, in the words of somebody tuning it.
GUIDANCE = """\
Answers, frame by frame, whether the footage is showing the behaviour. It asks
three questions in order: for each block, how much of its activity is rhythmic at
the rate you care about; across the frame, how many blocks are inside the value
range you called interesting; and over a window centred on the frame, whether
that many blocks stayed inside it long enough to be an event rather than a
twitch.

`freq_band` is in cycles per second and is about the behaviour's rhythm — the
stroke rate of grooming, the wingbeat, the step frequency. It is not about how
long an event lasts; that is `window_frames`.

`value_band` is in the units of whatever is feeding this node, which is why a
`temporal_baseline` upstream is worth having: it makes the band a number of
deviations that means the same thing in another replicate, instead of a number
about this recording's lighting.

`count_frac` is how much of the frame has to be involved, as a fraction of the
blocks — the difference between one animal moving and the whole dish stirring.
Left unset, nothing is claimed at all and the output is blank rather than
everything passing, which is deliberate: a fresh session should not look like one
continuous detection.

`window_frames` is how long the count has to hold. Centred means the window
straddles the frame it is answering for, using footage from both sides, which is
what you are looking at when you tune against a stretch you can already see —
keep it on. The cost is that a detection needs the frames after it before it can
be claimed, which SIEVE reads ahead for.

Every setting here is tuned by watching, so tune it on a stretch you have
already scrubbed through and can recognise. The output is one value per frame: 1
detected, 0 not, and blank where nothing is claimed."""


def _pool_size(workers: int) -> int | None:
    """`workers` as a `ThreadPoolExecutor` size; `None` is the stdlib default.

    `ALL_CORES` becomes `None` rather than `available_cpus()` on purpose. Doing
    the second would be this arithmetic holding a policy about how much of the
    machine a caller meant, and re-deriving "how much do I have" beside the one
    module whose subject that is, is exactly the second answer `resolve_workers`
    documents at length as the thing to avoid. The stdlib's own default is a
    third party to the disagreement rather than a party in it, and it is what
    "every core" already meant when this number went to `scipy.fft`.
    """
    return None if workers <= 0 else workers


# scipy.fft's stubs return `tuple[Dispatchable]` under a strict type checker;
# these three wrappers are where that unknowability is contained, so the
# transform code below stays fully typed.
def _fast_len(n: int) -> int:
    return int(cast(int, _fft.next_fast_len(n)))


def _fft_time_axis(x: FloatArray, n: int, workers: int) -> ComplexArray:
    return cast(ComplexArray, _fft.fft(x, n=n, axis=0, workers=workers))


def _ifft_time_axis(buf: ComplexArray, workers: int) -> ComplexArray:
    return cast(ComplexArray, _fft.ifft(buf, axis=0, workers=workers, overwrite_x=True))


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
    rather than stopping at its edge. A renderer should grade it, and any
    chunked evaluation must widen its chunks by it or seams ring.
    """
    return np.sqrt(2.0) * morlet_scales(freqs_hz)


def coi_edge_samples(freqs_hz: FloatArray, fs: float) -> FloatArray:
    """`coi_efolding_s` in samples at rate ``fs`` — the form a window
    declaration and a plot with a time axis in frames both need."""
    return coi_efolding_s(freqs_hz) * float(fs)


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
    what a batch or headless caller should have. A caller sharing the machine
    with decode threads passes a cap; see `mutual/shares.py`. It changes only
    how fast the answer arrives, never the answer.
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


def morlet_power_profile(
    x: FloatArray, fs: float, freqs_hz: FloatArray, *, workers: int = ALL_CORES
) -> NDArray[np.float32]:
    """Band power per frequency row, averaged over elements. (T, B) → (F, T).

    The scalogram a frequency band's handles are placed on: `morlet_power`'s
    cube with the element axis already averaged away. Written as its own loop
    rather than as that function plus a `.mean(axis=2)` because the cube is what
    it cannot afford to exist — a 24-row bank over a whole detection window of a
    block grid is hundreds of megabytes, spent on a picture. The two loops are
    otherwise the same loop, and the pad length is derived identically, so a row
    of this equals the same row of the cube averaged.

    The mean is over the *power* rather than the transform of a mean signal, and
    the difference is not cosmetic: transforming a mean cancels blocks moving out
    of phase with each other, which is most of what a dish of animals looks like.
    It is also the reduction that agrees with the chain — `inband_count` counts
    blocks whose own power is in band.
    """
    x32 = np.asarray(x, np.float32)
    if x32.ndim == 1:
        x32 = x32[:, None]
    n_frames = x32.shape[0]
    dt = 1.0 / fs
    scales = morlet_scales(freqs_hz)
    support = int(np.ceil(coi_efolding_s(freqs_hz).max() / dt * PAD_EFOLDINGS))
    n = _fast_len(n_frames + support)
    xf = _fft_time_axis(x32, n, workers)
    omega = 2.0 * np.pi * np.fft.fftfreq(n, d=dt)
    heavi = omega > 0
    out = np.empty((len(scales), n_frames), np.float32)
    buf = np.empty_like(xf)
    for i, s in enumerate(scales):
        np.multiply(xf, _daughter(float(s), omega, heavi, dt)[:, None], out=buf)
        w = _ifft_time_axis(buf, workers)[:n_frames]
        out[i] = (w.real**2 + w.imag**2).mean(axis=1)
    return out


def band_indices(freqs_hz: FloatArray, flo: float, fhi: float) -> tuple[int, int]:
    """Frequency rows ``[i, j)`` covering ``[flo, fhi]`` Hz on a sorted bank.

    An empty span snaps to the single nearest scale rather than raising or
    returning nothing: the band handles are continuous and the bank is
    discrete, so a user can legitimately place both handles between the same
    two rows, and a detector with zero scales in its band is a detector that
    silently went dead. A scalogram title renders the *snapped* band for the
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
    the band's scales, chunked over block columns so a whole-record pass stays
    memory-bounded.

    ``workers`` is how many block chunks are transformed at once, defaulting to
    every core unless the caller has someone to leave room for. **The pool is
    this module's, not `scipy.fft`'s.** v2 handed ``workers`` straight to
    `scipy.fft` and assumed it split the batch; on the build it shipped against
    it did not — 1, 2, 8, 16 and 32 workers timed identically on the strided
    ``axis=0`` call the transform actually makes *and* on a fully contiguous
    batch — so the whole ``(T, B)`` pass ran single-threaded while
    `mutual/shares.py` carefully budgeted threads for it. The chunk loop below
    is run on a `ThreadPoolExecutor` and the inner FFTs are told ``workers=1``,
    which measured 4.9x at eight threads on the reference stress workload and
    cannot silently become 1x again.

    **The pool cannot move a bit.** Chunks write disjoint column slices of one
    preallocated output and share nothing but read-only inputs, and the
    summation order *within* a chunk — the only place floats are added — is the
    serial order untouched. So the thread count is a wall-clock choice and never
    an answer, which is what `test_the_thread_count_cannot_move_a_bit` pins and
    what lets an interactive pass and a headless one be compared at all.
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
        k = min(max(i, 0), len(scales_all) - 1)
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
            # silent rather than as failed.
            for _ in pool.map(transform, starts):
                pass
    return out[:, 0] if squeeze else out


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
    Windows truncate at the record's edges and the returned effective length is
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

    The reason the window exists: a 1-frame spike of N blocks dilutes to N/W and
    cannot fake a sustained event. Prefix-sum, so the cost is O(T) regardless of
    W — this is on the cheap re-derive tier that runs on every threshold drag.
    ``window`` is in *frames*; the caller labels it in seconds.
    """
    c32 = np.asarray(count, np.float32)
    n_frames = c32.shape[0]
    if n_frames == 0 or window <= 1:
        return c32.astype(np.float32)
    c = np.concatenate([[0.0], np.cumsum(c32, dtype=np.float64)])
    hi, lo, neff = window_bounds(n_frames, window, centered)
    return ((c[hi] - c[lo]) / neff).astype(np.float32)


def count_band_to_counts(frac_lo: float, frac_hi: float, region_blocks: int) -> tuple[float, float]:
    """The one place a fractional count band becomes block counts.

    ``frac_lo``/``frac_hi`` are fractions of ``region_blocks`` (the number of
    blocks the detector's region holds — the denominator of every count it
    produces). Infinite endpoints pass through: "unbounded above" is not a
    fraction and does not denominate. Zero survives the multiply unchanged,
    which is correct — "at least none" is grid-independent.

    A fraction rather than v1's raw counts, and that is the deviation worth
    naming: v1 stored counts and carried them across grid changes with a
    re-denomination helper every caller had to remember, a measured 13x
    foot-gun. A fraction survives a block-size change by meaning the same thing.

    Raises:
        ValueError: if ``region_blocks`` is negative.
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

    ``start`` is added to both endpoints, so a gate computed over a window
    reports absolute source-frame intervals — the form a seeker's ticks and a
    prev/next jump consume, and the form Phase 5's table emitter writes rows in.
    """
    g = np.asarray(gate, bool)
    if not g.any():
        return []
    edges = np.diff(np.concatenate([[0], g.astype(np.int8), [0]]))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    return [(int(s + start), int(e + start)) for s, e in zip(starts, ends, strict=True)]


def wavelet_edge_frames(fps: float, freq_band: tuple[float, float]) -> int:
    """Frames of record either side of a target before the transform's pad
    stops reaching it.

    Charged on *both* sides, where v2's trailing kernel charged it only as
    history. The transform is two-sided whatever the detection window does, so
    a value computed with the pad on one side of it is not the value the whole
    record gives — which is the parity this tool is gated on.

    `PAD_EFOLDINGS` is the constant, and it is the conservative one of the two
    v2 measured for this: the pad's own leakage is at the float32 floor by
    three e-foldings, and the settling frontier v2's partial-record path used
    was narrower still. One constant covers both because the wider one does.
    """
    freqs = default_freqs(fps)
    i, j = band_indices(freqs, freq_band[0], freq_band[1])
    edge = coi_edge_samples(freqs[i:j], fps)
    if edge.size == 0:
        return 0
    return math.ceil(float(edge.max()) * PAD_EFOLDINGS)


#: The transform's reach at the corner of the legal parameter range: the lowest
#: bank frequency, at the highest rate a window may be denominated against.
MAX_WAVELET_EDGE_FRAMES = wavelet_edge_frames(MAX_FPS, (0.0, math.inf))

#: The worst case over the legal range, on each side of the target. The trailing
#: shape is what makes the two differ: it puts the whole detection window behind
#: the frame, so the history bound is `W - 1` while the read-ahead bound is only
#: what a centred window's forward half asks for.
MAX_WARMUP_FRAMES = max(MAX_WINDOW_FRAMES - 1, MAX_WAVELET_EDGE_FRAMES)
MAX_LOOKAHEAD_FRAMES = max(MAX_WINDOW_FRAMES - MAX_WINDOW_FRAMES // 2 - 1, MAX_WAVELET_EDGE_FRAMES)


def gate_series(series: FloatArray, params: DetectParams) -> NDArray[np.bool_] | None:
    """The whole chain over one ``(T, B)`` series: transform, count, mean, gate.

    v2's `detect/` package in one function, and `run` below is its only caller —
    the composition is what the tool *is*, so there is nothing left for a
    package to hold. What v2's version also returned was the intermediates a
    live tab plotted and a cheap-tier flag saying which of them could be reused.
    The intermediates are back, through `display` below and not through here:
    they are the pictures this tool's three bands are dragged on, and they leave
    on a channel that is not a product rather than as a second return value the
    executor would have to route. The cheap-tier flag stays cut — it is
    scheduling for a coalescer that does not exist.

    Returns:
        The per-frame gate, or `None` when the count threshold is unplaced —
        disarmed, which is not the same claim as armed and finding nothing.

    Raises:
        ValueError: if `series` is not a two-dimensional, non-empty
            `(frames, elements)` array.
    """
    power, _, windowed = _chain(_series2d(series), params)
    if params.count_frac is None:
        return None
    lo, hi = count_band_to_counts(params.count_frac[0], params.count_frac[1], power.shape[1])
    return detect_gate(windowed, lo, hi)


def _chain(
    series2d: NDArray[np.float32], params: DetectParams
) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.float32]]:
    """Per-block band power, the in-band count, and its windowed mean.

    Everything the chain derives before the threshold is applied, which is
    exactly what the gate and the display surfaces share. Two copies of these
    four lines would be two places for the transform's arguments to drift apart,
    and the drift would show as a value band whose handles cut a picture the
    detection was not computed from.
    """
    freqs = default_freqs(params.fps)
    i, j = band_indices(freqs, params.freq_band[0], params.freq_band[1])
    power = morlet_band_power(series2d, params.fps, freqs, i, j, workers=DETECTOR_WORKERS)
    count = inband_count(power, params.value_band[0], params.value_band[1])
    return power, count, windowed_mean(count, params.window_frames, params.centered)


def _series2d(series: FloatArray) -> NDArray[np.float32]:
    array = np.asarray(series, dtype=np.float32)
    if array.ndim != 2:
        raise ValueError(f"detect expects a 2D (frames, elements) series, got shape {array.shape}")
    if array.shape[0] == 0:
        raise ValueError("detect expects at least one frame")
    return array


def run(params: DetectParams, window: FrameSpan, state: None, /) -> Frame:
    """Derive the gate over the window, and emit the target frame's value.

    **The target is not the last frame of the window.** With a declared
    lookahead of `k` the executor hands over a window whose last `k` frames are
    past the frame being answered for, and the span says which frame that is
    (`core/tool_base.py`, `ToolRun`) — so `target_row` indexes the derived series
    at the same frame `FrameSpan.target` names, and neither can disagree with
    what the executor scheduled.

    The window is shorter than the declared one at the start of a run, where
    the history has not filled — the row still lands on the target, and the
    chain over a short record is the same chain.
    """
    series = _stacked(window)
    row = window.target_row
    gate = gate_series(series, params)
    value = np.nan if gate is None else float(gate[row])
    return Frame(
        data=np.array([[value]], dtype=np.float32),
        index=window[row].index,
        channels=ChannelSpec.GRAY,
    )


def _stacked(window: FrameSpan) -> NDArray[np.float32]:
    """The window as one ``(T, B)`` series, one row per frame."""
    return np.stack([np.asarray(frame.data, np.float32).reshape(-1) for frame in window])


def display(params: DetectParams, window: FrameSpan, /) -> dict[DisplaySurface, Frame]:
    """The three pictures this tool's bands are dragged on, at the target frame.

    One column of each surface per frame, which is the shape the loop can carry:
    the executor fills the channel frame by frame beside the output, and a front
    end assembles the picture from a span exactly as `SeriesCollector` assembles
    a trace. A surface delivered whole, once, would have to come from somewhere
    that has the whole span in hand, and the only such thing is the caller.

    Which band lands on which is the declaration, not this function's choice
    (`param_surfaces` below):

    - `freq_band` cuts rows out of the scalogram, so that surface is the whole
      bank rather than the band — the handles have to be draggable to somewhere
      they are not.
    - `value_band` cuts the per-block band power, which is many values per frame
      on one value axis. Those *are* the numbers `inband_count` compares, so the
      picture is the comparison rather than a summary of it.
    - `count_frac` cuts the windowed count, divided by the blocks it counts over
      so the handles read in the same fraction the parameter stores
      (`count_band_to_counts`).

    Costs a second derivation of the window on top of `run`'s, and the scalogram
    is the whole bank where the gate needs only the band's rows. That is why the
    channel is filled on request: a headless run draws nothing, and an
    interactive one draws for the node whose panel is open.
    """
    series = _stacked(window)
    row = window.target_row
    index = window[row].index
    power, _, windowed = _chain(_series2d(series), params)
    profile = morlet_power_profile(
        series, params.fps, default_freqs(params.fps), workers=DETECTOR_WORKERS
    )
    blocks = power.shape[1]
    return {
        DisplaySurface.SCALOGRAM: Frame(
            data=profile[:, row].reshape(-1, 1).astype(np.float32),
            index=index,
            channels=ChannelSpec.GRAY,
        ),
        DisplaySurface.TRACE: Frame(
            data=power[row].reshape(-1, 1).astype(np.float32),
            index=index,
            channels=ChannelSpec.GRAY,
        ),
        DisplaySurface.COUNT: Frame(
            # Zero blocks is a region with nothing in it, which `_series2d`
            # admits and every count over it is honestly nothing rather than a
            # division to guard.
            data=np.array([[float(windowed[row]) / blocks if blocks else 0.0]], np.float32),
            index=index,
            channels=ChannelSpec.GRAY,
        ),
    }


def _bank_axis(params: DetectParams) -> RowAxis:
    """The scalogram's rows as the frequencies they were taken at.

    `default_freqs` is already the bank the chain transforms on, so this is that
    call and not a second one: a declaration that derived the axis differently
    would put the handles on rows the detection was not computed from.
    """
    return RowAxis(tuple(float(hz) for hz in default_freqs(params.fps)))


@register_tool(
    tool_id="detect",
    version="1.0.0",
    summary="Morlet band power, value-band count, and detection gate as a per-frame channel.",
    accepts=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    emits=ArraySpec(dtypes=("float32",), channels=(ChannelSpec.GRAY,)),
    # Band power, the in-band count and the windowed mean are computed and none
    # of them leaves the node as a *product* — what a tool computes and what it
    # can emit are different lists, and this is the tool where they differ most.
    # The pictures they make do leave, on the display channel below, which is
    # not a product and is not on this list for that reason.
    emissions=(Emission("gate"),),
    run=run,
    # One value describing the source frame as a whole: the noun a count over
    # this node's output is denominated in is *frames*, where its input's was
    # blocks. The tool that consumes a grid and answers about the moment.
    element=ElementKind.FRAME,
    element_names=ElementNames("frame", "frames"),
    mode=Mode.WINDOWED,
    # The window is exact rather than settled-to-epsilon: past the declared
    # warmup the frames the chain reads are all in hand, so two runs over
    # different spans agree bit for bit.
    settling_epsilon=0.0,
    # Exact on both sides: the window is `2k+1` frames centred on the target
    # and nothing outside it is read.
    warmup_kind=WarmupKind.BOUNDED,
    guidance=GUIDANCE,
    primary_params=("freq_band", "value_band", "count_frac"),
    caption=(
        CaptionPart(label="freq", param="freq_band"),
        CaptionPart(label="value", param="value_band"),
        CaptionPart(label="count", param="count_frac"),
        CaptionPart(label="D", param="window_frames"),
    ),
    # This is the tool `BAND` was minted for: three pairs of handles dragged
    # along Hz, a block-power value, and a fraction, none of which is the
    # timeline `SPAN` hands off to.
    param_stereotypes={
        "freq_band": ParamStereotype.BAND,
        "value_band": ParamStereotype.BAND,
        "count_frac": ParamStereotype.BAND,
        "window_frames": ParamStereotype.SCALAR_RANGE,
        "centered": ParamStereotype.ENUM,
        "fps": ParamStereotype.SCALAR_RANGE,
    },
    # Three bands, three pictures, and no two of them the same picture — which
    # is why the surface is declared per parameter rather than once per tool.
    # The member names the plot and never the unit: Hz, the upstream node's own
    # units, and a fraction have no enum that could hold all three
    # (`core/tool_base.py`, `DisplaySurface`).
    param_surfaces={
        "freq_band": DisplaySurface.SCALOGRAM,
        "value_band": DisplaySurface.TRACE,
        "count_frac": DisplaySurface.COUNT,
    },
    # What a cut on each of those pictures is worth, which the picture itself
    # cannot say (`adr/a-parameters-space-is-resolved-by-the-graph.md`). One of
    # each form, and none of the three could have been written as another: the
    # bank is derived from a parameter, the fraction is a constant of the
    # quantity, and the value band is in units this tool never meets.
    param_axes={
        "freq_band": _bank_axis,
        "value_band": AxisRelation.INPUT_VALUES,
        "count_frac": ValueAxis((0.0, 1.0)),
    },
    display=display,
)
class DetectParams(ParamsBase):
    """The bands, the count threshold, and the window a detection is claimed on."""

    #: Frequency band in Hz over the Morlet bank; handles clamp to the bank.
    freq_band: tuple[float, float] = (0.0, math.inf)
    #: Value band over band power, in the incoming signal's own units.
    value_band: tuple[float, float] = (-math.inf, math.inf)
    #: Count threshold as fractions of the frame's elements, or None =
    #: disarmed. None is "nothing is claimed", not "everything passes".
    count_frac: tuple[float, float] | None = None
    #: The detection window, in frames.
    window_frames: int = Field(default=30, ge=1, le=MAX_WINDOW_FRAMES)
    #: Whether the window straddles its frame or trails it. Centred is what
    #: every tuned session in v2 looked at, and what this tool exists to make
    #: runnable (`adr/detector-is-a-node.md`).
    centered: bool = True
    #: Source frame rate, used to denominate the bank and the transform's
    #: reach. Explicit for `block_signal.fps`'s reason: a `run` is pure and
    #: cannot ask the graph what the container's rate was, so whatever
    #: configures the node writes it from a value it already owns.
    fps: float = Field(default=30.0, gt=0.0, le=MAX_FPS)

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
    def max_warmup_frames(cls) -> FrameCount:
        return FrameCount(MAX_WARMUP_FRAMES)

    @classmethod
    def max_lookahead_frames(cls) -> FrameCount:
        return FrameCount(MAX_LOOKAHEAD_FRAMES)

    def warmup_frames(self) -> FrameCount:
        """The wider of the window's history and the transform's reach.

        The bound is 1972 frames — a band reaching to 0.5 Hz at 240 fps — and
        the defaults need 247, which is what the refinement is worth here: every
        run would otherwise decode eight seconds of lead-in at 240 fps to
        answer for its first frame (`core/tool_base.py`).
        """
        return FrameCount(max(self._window_history(), self._wavelet_edge()))

    def lookahead_frames(self) -> FrameCount:
        """`warmup_frames` on the other side of the frame being emitted.

        Costs latency rather than decode, so the refinement matters more here
        than it does on the history side: the bound charged to every run would
        delay a preview by the widest window the model admits, against a frame
        of footage the user is looking at now.
        """
        return FrameCount(max(self._window_future(), self._wavelet_edge()))

    def _window_history(self) -> int:
        """Frames of the detection window that sit before its target."""
        if not self.centered:
            return self.window_frames - 1
        return self.window_frames // 2

    def _window_future(self) -> int:
        """Frames of the detection window that sit after its target.

        Zero when trailing, which is what makes that shape causal — and what
        made it the only shape v2 could run.
        """
        if not self.centered:
            return 0
        return self.window_frames - self.window_frames // 2 - 1

    def _wavelet_edge(self) -> int:
        return wavelet_edge_frames(self.fps, self.freq_band)
