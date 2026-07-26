"""Item 3's kernel: the three claims that make the signals trustworthy.

Each failure is a distinct lie the tab could tell: a static scene that
scores nonzero invents motion, a translation whose speed is wrong miscales
every threshold, and an aperture-degenerate block that reports noise
instead of zero turns "unmeasurable" into "event".
"""

from __future__ import annotations

from typing import cast

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from sieve.core.types import ChannelSpec, Frame
from sieve.filters.block_signal import (
    BlockSignalParams,
    BlockSignalState,
    Signal,
    auto_block,
    block_signal_cpu,
    grid_shape,
    resolve_block,
)

FPS = 30.0


def run_frames(
    frames: list[NDArray[np.float32]], params: BlockSignalParams
) -> list[NDArray[np.float32]]:
    """Feed a sequence through one state, the way one execute would."""
    state = BlockSignalState()
    out: list[NDArray[np.float32]] = []
    for i, data in enumerate(frames):
        frame = Frame(data=data, index=i, channels=ChannelSpec.GRAY)
        out.append(block_signal_cpu(frame, params, state).data)
    return out


def textured() -> NDArray[np.float32]:
    """A smooth random field: enough 2-D texture that LK is well-posed."""
    gen = np.random.default_rng(3)
    rough = gen.uniform(0, 255, (96, 96)).astype(np.float32)
    return cast(NDArray[np.float32], cv2.GaussianBlur(rough, (0, 0), 3.0))


def test_static_input_is_exactly_zero_for_both_signals() -> None:
    still = textured()
    for signal in (Signal.CHANGE_ENERGY, Signal.FLOW_SPEED):
        params = BlockSignalParams(signal=signal, block=16, fps=FPS)
        outs = run_frames([still, still, still], params)
        for out in outs:
            assert out.shape == (6, 6)
            np.testing.assert_array_equal(out, 0.0)


def test_uniform_translation_measures_its_own_speed() -> None:
    # One pixel per frame of coherent translation should read ~1 * fps px/s,
    # and change_energy must see it too. Judged on interior blocks — the roll
    # wraps at the edges and np.gradient one-sides there.
    field = textured()
    frames = [np.roll(field, shift=i, axis=1) for i in range(3)]

    speed = run_frames(frames, BlockSignalParams(signal=Signal.FLOW_SPEED, block=16, fps=FPS))[2]
    interior = speed[1:-1, 1:-1]
    assert float(np.median(interior)) == pytest.approx(FPS, rel=0.15)

    energy = run_frames(frames, BlockSignalParams(signal=Signal.CHANGE_ENERGY, block=16, fps=FPS))[
        2
    ]
    assert float(energy[1:-1, 1:-1].min()) > 0.0


def test_aperture_degenerate_input_reports_exactly_zero_not_noise() -> None:
    # Stripes varying only along x, translated along y: the motion is real
    # but no local measurement can see it. The determinant guard must return
    # exactly zero — a near-zero divide would return enormous noise instead.
    x = np.arange(96, dtype=np.float32)
    stripes = np.tile(128.0 + 64.0 * np.sin(x / 4.0), (96, 1)).astype(np.float32)
    frames = [np.roll(stripes, shift=i, axis=0) for i in range(3)]

    speed = run_frames(frames, BlockSignalParams(signal=Signal.FLOW_SPEED, block=16, fps=FPS))[2]
    np.testing.assert_array_equal(speed, 0.0)


def test_block_resolution_is_the_one_source_of_grid_truth() -> None:
    # auto = 64 source px at scale; explicit block wins; the grid ceils so
    # ragged edges are real blocks. These three numbers denominate the count
    # threshold, so they are pinned as arithmetic.
    assert auto_block(0.25) == 16
    assert resolve_block(0, 0.25) == 16
    assert resolve_block(24, 0.25) == 24
    assert grid_shape(96, 100, 16) == (6, 7)
