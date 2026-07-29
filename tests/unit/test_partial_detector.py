

















from __future__ import annotations

import numpy as np

from sieve.core.detection import settled_frames as settled_after_window
from sieve.core.wavelet import (
    COI_SETTLE_EFOLDINGS,
    coi_edge_samples,
    default_freqs,
    settled_frames,
)
from sieve.gui.chain_model import DetectorState
from sieve.gui.detector_worker import DetectorRequest, derive, settled_for

FPS = 20.0


def _series(frames: int, blocks: int = 12, *, seed: int = 0) -> np.ndarray:

    rng = np.random.default_rng(seed)
    data = rng.random((frames, 3, blocks // 3), dtype=np.float32) * 0.1
    data[frames // 3 : frames // 2] += 5.0
    return data.astype(np.float32)


def test_a_partial_pass_stops_short_of_the_cone_of_influence() -> None:






    frames = 400
    freqs = default_freqs(FPS)
    settled = settled_frames(frames, FPS, freqs)

    assert settled < frames, "a truncated record cannot be settled to its cut"
    edge = float(coi_edge_samples(freqs, FPS).max())
    assert frames - settled >= edge * COI_SETTLE_EFOLDINGS, (
        "the held-back wedge must cover the measured settling distance, not one e-folding"
    )






    high = freqs[freqs >= freqs[len(freqs) // 2]]
    assert settled_frames(frames, FPS, high) > settled


def test_an_empty_band_settles_nothing_rather_than_raising() -> None:







    assert settled_frames(200, FPS, np.array([])) == 0
    assert settled_frames(0, FPS, default_freqs(FPS)) == 0


def test_a_centered_window_pulls_the_frontier_further_back_than_a_trailing_one() -> None:






    frames = 200
    assert settled_after_window(frames, 40, centered=False) == frames
    assert settled_after_window(frames, 40, centered=True) < frames


    assert settled_after_window(frames, 80, centered=True) < settled_after_window(
        frames, 40, centered=True
    )


def test_a_partial_gate_never_claims_a_detection_it_will_later_withdraw() -> None:
















    whole = _series(400)
    state = DetectorState(
        value_band=(0.5, np.inf),
        count_frac=(0.25, 1.0),
        window_frames=20,
        centered=True,
    )

    def gate_of(data: np.ndarray, *, final: bool) -> np.ndarray:
        result = derive(
            DetectorRequest(
                revision=1, series=data, start_index=0, fps=FPS, state=state, final=final
            )
        )
        assert result.update.gate is not None
        return np.asarray(result.update.gate)

    final = gate_of(whole, final=True)
    for cut in (200, 280, 360):
        partial = gate_of(whole[:cut], final=False)
        settled = len(partial)
        assert settled > 0, f"cut {cut} settled nothing — the fixture cannot prove anything"
        assert partial.any(), f"cut {cut} detected nothing — the band must actually bite"
        withdrawn = np.flatnonzero(partial & ~final[:settled])
        assert withdrawn.size == 0, (
            f"cut {cut} gated frames {withdrawn.tolist()} that the final pass ungates"
        )


def test_a_final_pass_claims_the_whole_record_and_a_partial_one_does_not() -> None:






    data = _series(160)
    state = DetectorState(count_frac=(0.05, 1.0), window_frames=20, centered=True)
    common = {"revision": 1, "series": data, "start_index": 0, "fps": FPS, "state": state}

    final = derive(DetectorRequest(**common, final=True))
    partial = derive(DetectorRequest(**common, final=False))

    assert final.settled == final.frames == 160
    assert partial.settled < partial.frames
    assert settled_for(160, FPS, state, final=True) == 160




    assert np.array_equal(final.update.windowed, partial.update.windowed)


def test_the_start_index_survives_so_intervals_are_absolute() -> None:






    data = _series(200)
    state = DetectorState(count_frac=(0.05, 1.0), window_frames=20, centered=True)
    result = derive(
        DetectorRequest(revision=1, series=data, start_index=500, fps=FPS, state=state, final=False)
    )
    assert result.start_index == 500
    assert result.update.intervals is not None
    assert all(start >= 500 for start, _ in result.update.intervals)


def test_the_density_surface_is_binned_here_and_matches_its_own_array() -> None:












    data = _series(120, blocks=12)
    state = DetectorState(count_frac=(0.05, 1.0), window_frames=20, centered=True)
    result = derive(
        DetectorRequest(revision=1, series=data, start_index=0, fps=FPS, state=state, final=True)
    )

    assert result.density.blocks == result.update.band_power.shape[1]
    assert result.density.argb.shape[1] == result.update.band_power.shape[0]
    assert result.density.value_max == float(result.update.band_power.max())
    assert result.density_ms >= 0.0
