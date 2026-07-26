"""The chain model's grading, disarm, and reset rules — item 6's Qt-free core.

Each failure is a different way the stack could lie: a grade that throws
cannot draw a broken chain at all, a conflict graded past the first mismatch
paints repairable chains as wrecks, an unset threshold that gates paints a
fresh tab green, and a Reset that touches structure deletes the user's work.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from sieve.gui.chain_model import (
    ChainKind,
    DetectorState,
    Status,
    parity_chain,
    recompute,
)

FPS = 30.0


def test_grade_ok_removal_conflict_and_loaded_broken() -> None:
    chain = parity_chain(FPS)
    assert [g.status for g in chain.grades()] == [Status.OK] * 5

    # Removal breaks the chain mid-way: morlet_band now receives an image.
    broken = chain.without("block_signal")
    statuses = [g.status for g in broken.grades()]
    assert statuses == [Status.OK, Status.OK, Status.CONFLICT, Status.UNREACHED]
    conflict = broken.grades()[2]
    assert "expects block series" in conflict.message
    assert "receiving image" in conflict.message
    assert not broken.detection_reachable()

    # A loaded file can be broken at the head too: everything after the
    # first conflict is unreached, not a cascade of conflicts.
    headless = replace(chain, steps=chain.steps[3:])
    assert [g.status for g in headless.grades()] == [Status.CONFLICT, Status.UNREACHED]


def test_runnable_prefix_survives_a_broken_suffix() -> None:
    # "No reachable step, no graph" is about the graphs; the video still
    # previews through whatever node-backed prefix is intact.
    chain = parity_chain(FPS)
    full = chain.pipeline()
    assert [n.filter_id for n in full.nodes] == ["rescale", "normalize", "block_signal"]
    assert len(full.edges) == 2

    broken = chain.without("normalize")  # image->image gap closes; still ok
    assert [g.status for g in broken.grades()] == [Status.OK] * 4
    assert [n.filter_id for n in broken.pipeline().nodes] == ["rescale", "block_signal"]

    headless = chain.without("block_signal")
    assert [n.filter_id for n in headless.pipeline().nodes] == ["rescale", "normalize"]


def test_disarmed_detector_produces_no_gate_and_armed_detects() -> None:
    rng = np.random.default_rng(5)
    series = rng.random((120, 8)).astype(np.float32)
    series[40:80] += 10.0  # a sustained loud stretch

    disarmed = DetectorState.default(FPS)
    update = recompute(series, FPS, disarmed, start_index=200)
    assert update.gate is None and update.intervals is None
    assert update.count.shape == (120,)  # the signal still derives

    armed = replace(disarmed, count_frac=(0.5, math.inf), value_band=(5.0, math.inf))
    hot = recompute(series, FPS, armed, start_index=200, band_power=update.band_power)
    assert hot.intervals is not None and len(hot.intervals) == 1
    start, end = hot.intervals[0]
    assert start >= 200  # absolute frames, not series offsets
    assert end > start


def test_reset_restores_knobs_and_disarms_but_keeps_structure() -> None:
    defaults = parity_chain(FPS)
    chain = parity_chain(FPS)
    # The user tunes: swaps the signal, arms the detector, drops normalize.
    tuned_steps = tuple(
        replace(
            s,
            node=s.node.model_copy(update={"params": {**s.node.params, "signal": "flow_speed"}}),
        )
        if s.step_id == "block_signal" and s.node
        else s
        for s in chain.without("normalize").steps
    )
    tuned = replace(
        chain,
        steps=tuned_steps,
        detector=replace(chain.detector, count_frac=(0.3, math.inf), window_frames=90),
    )

    fresh = tuned.reset(defaults)
    # Structure kept: normalize stays gone.
    assert [s.step_id for s in fresh.steps] == [s.step_id for s in tuned.steps]
    # Knobs back: the signal swap is undone.
    signal_step = next(s for s in fresh.steps if s.step_id == "block_signal")
    assert signal_step.node is not None
    assert signal_step.node.params["signal"] == "change_energy"
    # Detector back to documented defaults: disarmed, D of one second.
    assert not fresh.detector.armed
    assert fresh.detector.window_frames == round(FPS)


def test_kinds_are_not_derivable_from_filter_specs() -> None:
    # The reason grade() exists GUI-side: both an image step and the block
    # step emit GRAY float32 per FilterSpec, so the chain model's kinds carry
    # a distinction the type system cannot (the cannot-type-vision finding).
    chain = parity_chain(FPS)
    kinds = {s.step_id: (s.kind_in, s.kind_out) for s in chain.steps}
    assert kinds["normalize"] == (ChainKind.IMAGE, ChainKind.IMAGE)
    assert kinds["block_signal"] == (ChainKind.IMAGE, ChainKind.BLOCK_SERIES)
