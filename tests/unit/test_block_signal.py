







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

    state = BlockSignalState()
    out: list[NDArray[np.float32]] = []
    for i, data in enumerate(frames):
        frame = Frame(data=data, index=i, channels=ChannelSpec.GRAY)
        out.append(block_signal_cpu(frame, params, state).data)
    return out


def textured() -> NDArray[np.float32]:

    gen = np.random.default_rng(3)
    rough = gen.uniform(0, 255, (96, 96)).astype(np.float32)
    return cast(NDArray[np.float32], cv2.GaussianBlur(rough, (0, 0), 3.0))


def test_static_input_is_exactly_zero_for_every_signal() -> None:



    still = textured()
    for signal in Signal:
        params = BlockSignalParams(signal=signal, block=16, fps=FPS)
        outs = run_frames([still, still, still], params)
        for out in outs:
            assert out.shape == (6, 6)
            np.testing.assert_array_equal(out, 0.0)


def test_uniform_translation_measures_its_own_speed() -> None:



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



    x = np.arange(96, dtype=np.float32)
    stripes = np.tile(128.0 + 64.0 * np.sin(x / 4.0), (96, 1)).astype(np.float32)
    frames = [np.roll(stripes, shift=i, axis=0) for i in range(3)]

    speed = run_frames(frames, BlockSignalParams(signal=Signal.FLOW_SPEED, block=16, fps=FPS))[2]
    np.testing.assert_array_equal(speed, 0.0)


def test_coherence_separates_translation_from_change_in_place() -> None:




    field = textured()
    params = BlockSignalParams(signal=Signal.COHERENCE, block=16, fps=FPS)

    walking = run_frames([np.roll(field, i, axis=1) for i in range(3)], params)[2]
    assert float(np.median(walking[1:-1, 1:-1])) > 0.8

    gen = np.random.default_rng(9)
    pattern = cv2.GaussianBlur(gen.uniform(0, 255, field.shape).astype(np.float32), (0, 0), 3.0)
    flicker = cast(NDArray[np.float32], field + 0.5 * (pattern - float(pattern.mean())))
    grooming = run_frames([field, flicker, field], params)[2]
    assert float(np.median(grooming[1:-1, 1:-1])) < 0.2


def test_opposing_motions_in_one_block_read_incoherent() -> None:






    field = textured()
    moved = np.vstack([np.roll(field[:48], 2, axis=1), np.roll(field[48:], -2, axis=1)])
    params = BlockSignalParams(signal=Signal.COHERENCE, block=96, fps=FPS)
    out = run_frames([field, moved], params)[1]
    assert out.shape == (1, 1)
    assert float(out[0, 0]) < 0.2


def test_flow_agreement_spans_its_two_poles() -> None:





    field = textured()
    params = BlockSignalParams(signal=Signal.FLOW_AGREEMENT, block=16, fps=FPS)
    walking = run_frames([np.roll(field, i, axis=1) for i in range(3)], params)[2]
    assert float(np.median(walking[1:-1, 1:-1])) > 0.9

    moved = np.vstack([np.roll(field[:48], 2, axis=1), np.roll(field[48:], -2, axis=1)])
    one_block = BlockSignalParams(signal=Signal.FLOW_AGREEMENT, block=96, fps=FPS)
    out = run_frames([field, moved], one_block)[1]
    assert out.shape == (1, 1)
    assert float(out[0, 0]) < 0.2


def test_flow_agreement_is_zero_where_nothing_resolved_not_one() -> None:






    x = np.arange(96, dtype=np.float32)
    stripes = np.tile(128.0 + 64.0 * np.sin(x / 4.0), (96, 1)).astype(np.float32)
    frames = [np.roll(stripes, shift=i, axis=0) for i in range(3)]
    out = run_frames(frames, BlockSignalParams(signal=Signal.FLOW_AGREEMENT, block=16, fps=FPS))[2]
    np.testing.assert_array_equal(out, 0.0)


def test_flow_agreement_reads_only_the_pixels_that_moved() -> None:





    field = textured()
    half = field.copy()
    half[48:] = 128.0
    moved = half.copy()
    moved[:48] = np.roll(field[:48], 2, axis=1)
    params = BlockSignalParams(signal=Signal.FLOW_AGREEMENT, block=96, fps=FPS)
    out = run_frames([half, moved], params)[1]
    assert out.shape == (1, 1)
    assert float(out[0, 0]) > 0.8


def test_every_signal_has_a_label_on_the_quick_switch() -> None:




    from sieve.gui.chain_model import SIGNAL_LABELS

    assert set(SIGNAL_LABELS) == {s.value for s in Signal}


def test_block_resolution_is_the_one_source_of_grid_truth() -> None:



    assert auto_block(0.25) == 16
    assert resolve_block(0, 0.25) == 16
    assert resolve_block(24, 0.25) == 24
    assert grid_shape(96, 100, 16) == (6, 7)
