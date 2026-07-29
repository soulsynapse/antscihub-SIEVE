







from __future__ import annotations

import numpy as np

from sieve.core.wavelet import (
    band_indices,
    coi_efolding_s,
    default_freqs,
    morlet_band_power,
    morlet_power,
)

FPS = 30.0


def test_pure_tone_concentrates_in_nearest_scale_row() -> None:






    freqs = default_freqs(FPS)
    row = 12


    t = np.arange(int(20 * FPS)) / FPS
    tone = np.sin(2.0 * np.pi * float(freqs[row]) * t).astype(np.float32)
    power = morlet_power(tone, FPS, freqs)

    mid = power.shape[1] // 2
    assert int(np.argmax(power[:, mid])) == row


def test_band_indices_empty_span_snaps_to_one_scale() -> None:





    freqs = default_freqs(FPS)

    flo = float(freqs[10]) * 1.01
    fhi = float(freqs[11]) * 0.99
    i, j = band_indices(freqs, flo, fhi)
    assert j - i == 1

    assert i in (10, 11)


def test_band_power_matches_cube_slice_exactly() -> None:







    rng = np.random.default_rng(7)
    x = rng.standard_normal((400, 6)).astype(np.float32)
    freqs = default_freqs(FPS)
    i, j = 8, 15
    cube = morlet_power(x, FPS, freqs)
    direct = cube[i:j].sum(axis=0)
    banded = morlet_band_power(x, FPS, freqs, i, j, block_chunk=4)
    np.testing.assert_array_equal(banded, direct)


def test_the_thread_count_cannot_move_a_bit() -> None:















    rng = np.random.default_rng(11)
    x = rng.standard_normal((256, 11)).astype(np.float32)
    freqs = default_freqs(FPS)
    i, j = 6, 13
    serial = morlet_band_power(x, FPS, freqs, i, j, block_chunk=3, workers=1)
    for workers in (2, 4, -1):
        threaded = morlet_band_power(x, FPS, freqs, i, j, block_chunk=3, workers=workers)
        np.testing.assert_array_equal(threaded, serial)


def test_coi_efolding_is_1p369_over_f() -> None:



    freqs = np.array([0.5, 2.0, 20.0])
    np.testing.assert_allclose(coi_efolding_s(freqs), 1.3693 / freqs, rtol=1e-3)
