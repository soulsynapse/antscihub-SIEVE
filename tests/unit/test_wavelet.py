"""Pins on `tools/detect.py`'s transform — the claims the parity plan names.

Each test fails for a distinct real reason: a wrong scale relation smears a
tone across rows, a broken snap makes an empty band a dead detector, and a
band sum padded to the band's own support instead of the bank's stops
matching the cube slice it claims to equal.
"""

from __future__ import annotations

import numpy as np

from sieve.tools.detect import (
    band_indices,
    coi_efolding_s,
    default_freqs,
    morlet_band_power,
    morlet_power,
)

FPS = 30.0


def test_pure_tone_concentrates_in_nearest_scale_row() -> None:
    """A 4 Hz tone's power peaks in the bank row nearest 4 Hz.

    This is the scale relation itself: if `morlet_scales` mapped frequency to
    scale wrongly, the peak would land in a different row and every band the
    user drags would filter a different frequency than its label claims.
    """
    freqs = default_freqs(FPS)
    row = 12  # ~3.2 Hz; any interior row works, an exact bank frequency is
    # the unambiguous case (a tone midway between two log-spaced rows is
    # legitimately claimed by either)
    t = np.arange(int(20 * FPS)) / FPS
    tone = np.sin(2.0 * np.pi * float(freqs[row]) * t).astype(np.float32)
    power = morlet_power(tone, FPS, freqs)
    # Judge at the record's center, well inside every scale's COI.
    mid = power.shape[1] // 2
    assert int(np.argmax(power[:, mid])) == row


def test_band_indices_empty_span_snaps_to_one_scale() -> None:
    """Both handles between the same two rows still selects exactly one row.

    The failure this closes is a detector that silently goes dead when the
    continuous handles land in a gap of the discrete bank.
    """
    freqs = default_freqs(FPS)
    # A span strictly inside the gap between rows 10 and 11.
    flo = float(freqs[10]) * 1.01
    fhi = float(freqs[11]) * 0.99
    i, j = band_indices(freqs, flo, fhi)
    assert j - i == 1
    # And the snapped row is the nearest one to the span.
    assert i in (10, 11)


def test_band_power_matches_cube_slice_exactly() -> None:
    """`morlet_band_power` equals the full cube's band sum, bit for bit.

    The memory-bounded path derives its zero-pad length from the whole bank,
    not the band — pad to the band's own support instead and the FFT length
    changes, the two disagree in the last ulp first and visibly at the record
    ends, and the whole-clip pass stops reproducing the preview.
    """
    rng = np.random.default_rng(7)
    x = rng.standard_normal((400, 6)).astype(np.float32)
    freqs = default_freqs(FPS)
    i, j = 8, 15
    cube = morlet_power(x, FPS, freqs)
    direct = cube[i:j].sum(axis=0)
    banded = morlet_band_power(x, FPS, freqs, i, j, block_chunk=4)
    np.testing.assert_array_equal(banded, direct)


def test_the_thread_count_cannot_move_a_bit() -> None:
    """One thread and many produce the same array, exactly.

    `morlet_band_power` runs its block-chunk loop on a thread pool of the
    caller's size, so a live tab pass (a small share of the machine) and a
    headless whole-clip pass (all of it) are two different thread counts over
    the same input. If those disagreed anywhere — a shared scratch buffer, a
    chunk boundary that moved with the pool, an accumulation order that
    depended on completion order — the parity check comparing a live tuning to
    a batch run would be comparing two answers and calling the difference a
    finding.

    More chunks than threads on purpose: `block_chunk=3` over 11 columns is
    four chunks, one of them partial, so chunk-boundary arithmetic and the
    ragged tail are both under the pool rather than beside it.
    """
    rng = np.random.default_rng(11)
    x = rng.standard_normal((256, 11)).astype(np.float32)
    freqs = default_freqs(FPS)
    i, j = 6, 13
    serial = morlet_band_power(x, FPS, freqs, i, j, block_chunk=3, workers=1)
    for workers in (2, 4, -1):
        threaded = morlet_band_power(x, FPS, freqs, i, j, block_chunk=3, workers=workers)
        np.testing.assert_array_equal(threaded, serial)


def test_coi_efolding_is_1p369_over_f() -> None:
    """The w0=6 e-folding time is ~1.369/f s — the constant the alpha fade
    and any chunk widening are built on (a 1.46/f figure circulated once and
    was ~7% too large)."""
    freqs = np.array([0.5, 2.0, 20.0])
    np.testing.assert_allclose(coi_efolding_s(freqs), 1.3693 / freqs, rtol=1e-3)
