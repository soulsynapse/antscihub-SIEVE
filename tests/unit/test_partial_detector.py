"""What a partial detector pass is allowed to claim about a record still filling.

Three claims, each failing for a different real reason:

* a partial pass that read to the end of its record would publish values the
  transform's zero-padding invented, and they would visibly change on the next
  pass;
* a gate drawn past the settled frontier would put detection ticks on the
  seeker that later vanish, which is navigation lying rather than a graph being
  incomplete;
* a *final* pass held back by the same arithmetic would leave the last seconds
  of every finished render permanently ungated — the frontier is about a record
  still growing, and a render that is over has none.

Qt-free on purpose: `derive` and `settled_for` are arithmetic, and the rules
worth pinning here should not need an event loop or a thread to reach.
"""

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
    """A `(T, ny, nx)` block-grid series with a burst in the middle."""
    rng = np.random.default_rng(seed)
    data = rng.random((frames, 3, blocks // 3), dtype=np.float32) * 0.1
    data[frames // 3 : frames // 2] += 5.0
    return data.astype(np.float32)


def test_a_partial_pass_stops_short_of_the_cone_of_influence() -> None:
    """The frontier is the widest e-folding time in the *band*, not the bank.

    At 0.5 Hz the COI is ~2.74 s — 55 frames here — so a 200-frame partial
    record settles well short of its own end. A pass that claimed all 200 would
    be publishing the zero-pad as data.
    """
    frames = 400
    freqs = default_freqs(FPS)
    settled = settled_frames(frames, FPS, freqs)

    assert settled < frames, "a truncated record cannot be settled to its cut"
    edge = float(coi_edge_samples(freqs, FPS).max())
    assert frames - settled >= edge * COI_SETTLE_EFOLDINGS, (
        "the held-back wedge must cover the measured settling distance, not one e-folding"
    )

    # A band that excludes the low frequencies settles much closer to the cut:
    # contamination comes from the daughters actually summed, so denominating
    # on the whole bank would withhold graph the transform had finished with.
    # `default_freqs` caps at 0.45 * fps, so this band is chosen from the bank
    # rather than assumed — at 20 fps the top row is 9 Hz, not 25.
    high = freqs[freqs >= freqs[len(freqs) // 2]]
    assert settled_frames(frames, FPS, high) > settled


def test_an_empty_band_settles_nothing_rather_than_raising() -> None:
    """Public `core/` arithmetic answers conservatively instead of refusing.

    `band_indices` cannot hand this an empty span — it snaps to the nearest
    scale — but a caller computing frequencies some other way would otherwise
    get a bare `max()` failure out of a reduction, which says nothing about
    what it did wrong.
    """
    assert settled_frames(200, FPS, np.array([])) == 0
    assert settled_frames(0, FPS, default_freqs(FPS)) == 0


def test_a_centered_window_pulls_the_frontier_further_back_than_a_trailing_one() -> None:
    """The second frontier: a centered D window reads frames not yet decoded.

    A trailing window never looks forward, so truncation costs it nothing. A
    centered one averages against frames that have not arrived and reports a
    mean that changes when they do.
    """
    frames = 200
    assert settled_after_window(frames, 40, centered=False) == frames
    assert settled_after_window(frames, 40, centered=True) < frames
    # Widening the window pulls the frontier further back — this is what makes
    # the tab recompute it on a D drag rather than remember the worker's.
    assert settled_after_window(frames, 80, centered=True) < settled_after_window(
        frames, 40, centered=True
    )


def test_a_partial_gate_never_claims_a_detection_it_will_later_withdraw() -> None:
    """No frame the partial pass gated on is ungated by the final one.

    The load-bearing claim of the whole design. Detection ticks drive the
    seeker's prev/next jumps, so a detection that appears and then vanishes as
    the record grows is worse than a graph that has not got there yet.

    Stated per *frame*, not per interval, because the interval form is not the
    claim: a run that reaches the settled frontier legitimately grows longer as
    the record does, so `(0, 125)` becoming `(0, 300)` is the design working
    rather than a withdrawal. What must never happen is a frame flipping from
    gated to ungated, and that is what this asserts.

    The value band is deliberately narrow. With a wide-open band `inband_count`
    counts every finite block whatever its magnitude, the count stops depending
    on band power at all, and the test would pass without exercising anything.
    """
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
    """`final` is what separates a moving frontier from the clip's own edge.

    Without this a finished render would leave its last seconds permanently
    ungated — the detector would be blind to the end of every working window,
    which is precisely where a user drags the window to look.
    """
    data = _series(160)
    state = DetectorState(count_frac=(0.05, 1.0), window_frames=20, centered=True)
    common = {"revision": 1, "series": data, "start_index": 0, "fps": FPS, "state": state}

    final = derive(DetectorRequest(**common, final=True))  # pyright: ignore[reportArgumentType]
    partial = derive(DetectorRequest(**common, final=False))  # pyright: ignore[reportArgumentType]

    assert final.settled == final.frames == 160
    assert partial.settled < partial.frames
    assert settled_for(160, FPS, state, final=True) == 160

    # Both derive the same curves over the same data — only what they are
    # allowed to *claim* differs. A design where the partial path computed
    # something different would make the graphs jump on the last pass.
    assert np.array_equal(final.update.windowed, partial.update.windowed)


def test_the_start_index_survives_so_intervals_are_absolute() -> None:
    """A window that does not start at frame zero still reports source frames.

    The seeker jumps to these numbers. An off-by-start here would send the
    playhead to the wrong place in the clip, silently and only for windows the
    user had moved.
    """
    data = _series(200)
    state = DetectorState(count_frac=(0.05, 1.0), window_frames=20, centered=True)
    result = derive(
        DetectorRequest(revision=1, series=data, start_index=500, fps=FPS, state=state, final=False)
    )
    assert result.start_index == 500
    assert result.update.intervals is not None
    assert all(start >= 500 for start, _ in result.update.intervals)


def test_the_density_surface_is_binned_here_and_matches_its_own_array() -> None:
    """The picture crosses back with the pass that produced it.

    The failure this closes is silent: if `derive` stopped carrying a surface
    the GUI thread would fall back to binning one itself in `set_series`, the
    graphs would look identical, and the whole cost this arrangement exists to
    move would be back on the thread it was moved off — visible only as a
    session that stutters at large B.

    The surface is checked against `band_power`'s own shape and maximum rather
    than merely being non-None, because a surface for the *wrong* array is the
    one wrong answer that still renders.
    """
    data = _series(120, blocks=12)
    state = DetectorState(count_frac=(0.05, 1.0), window_frames=20, centered=True)
    result = derive(
        DetectorRequest(revision=1, series=data, start_index=0, fps=FPS, state=state, final=True)
    )

    assert result.density.blocks == result.update.band_power.shape[1]
    assert result.density.argb.shape[1] == result.update.band_power.shape[0]
    assert result.density.value_max == float(result.update.band_power.max())
    assert result.density_ms >= 0.0
