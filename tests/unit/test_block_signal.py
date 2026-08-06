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


def test_static_input_is_exactly_zero_for_every_signal() -> None:
    # Coherence is the interesting case: with zero temporal change the t-axis
    # is a null direction of the tensor and the raw scalar would read a
    # vacuous 1. The zero-change gate is what this pins.
    still = textured()
    for signal in Signal:
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


def test_coherence_separates_translation_from_change_in_place() -> None:
    # The two poles of the discriminant: a texture translating as a piece has
    # a rank-deficient block tensor (one (u, v) explains everything) and must
    # score near 1; the same texture with an independent pattern added in
    # place has no translation that explains its change and must score near 0.
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
    # Two halves of a single 96 px block translating in opposite directions:
    # each pixel is locally coherent, the block is not. This is the test that
    # fails if the eigendecomposition is moved before the block reduction —
    # per-pixel tensors are near rank-one, every pixel votes "coherent", and
    # averaging those votes scores this block high (measured 0.50 against the
    # correct order's 0.01).
    field = textured()
    moved = np.vstack([np.roll(field[:48], 2, axis=1), np.roll(field[48:], -2, axis=1)])
    params = BlockSignalParams(signal=Signal.COHERENCE, block=96, fps=FPS)
    out = run_frames([field, moved], params)[1]
    assert out.shape == (1, 1)
    assert float(out[0, 0]) < 0.2


def test_flow_agreement_spans_its_two_poles() -> None:
    # The scale's ends. A texture translating as a piece has every measurable
    # pixel pointing the same way and must read ~1; two halves of one block
    # translating in opposite directions cancel and must read ~0. A mean of
    # `atan2` instead of a mean of unit vectors fails the second — opposite
    # angles average to a direction nobody moved in, at full resultant length.
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
    # Stripes varying only along x, translated along y: real motion, no local
    # measurement can see it. Every pixel is excluded, so the block has no
    # unit vectors to average. Zero is the honest report; the failure this
    # guards against is the opposite one — an unmeasured block whose empty
    # circular mean is treated as perfect agreement and renders as a
    # confident 1, which is rule 6 exactly.
    x = np.arange(96, dtype=np.float32)
    stripes = np.tile(128.0 + 64.0 * np.sin(x / 4.0), (96, 1)).astype(np.float32)
    frames = [np.roll(stripes, shift=i, axis=0) for i in range(3)]
    out = run_frames(frames, BlockSignalParams(signal=Signal.FLOW_AGREEMENT, block=16, fps=FPS))[2]
    np.testing.assert_array_equal(out, 0.0)


def test_flow_agreement_reads_only_the_pixels_that_moved() -> None:
    # Half the block is featureless floor, half is texture translating as a
    # piece. Agreement is the resultant over the *measured* pixels, so it must
    # still read high — normalising by the block's pixel count instead would
    # halve it, and the block would report "half the pixels disagreed" about a
    # scene in which nothing disagreed with anything.
    field = textured()
    half = field.copy()
    half[48:] = 128.0
    moved = half.copy()
    moved[:48] = np.roll(field[:48], 2, axis=1)
    params = BlockSignalParams(signal=Signal.FLOW_AGREEMENT, block=96, fps=FPS)
    out = run_frames([half, moved], params)[1]
    assert out.shape == (1, 1)
    assert float(out[0, 0]) > 0.8


def test_every_signal_has_a_declared_presentation_label() -> None:
    # The enum is discovered from the filter and the labels live on the same
    # spec presentation channel the GUI reads. A signal the kernel computes but
    # cannot name now fails in the filter's declaration, not in a widget map.
    labels = BlockSignalParams.spec().param_value_labels["signal"]

    assert set(labels) == {s.value for s in Signal}
    assert all(label for label in labels.values())


def test_block_resolution_is_the_one_source_of_grid_truth() -> None:
    # auto = 64 source px at scale; explicit block wins; the grid ceils so
    # ragged edges are real blocks. These three numbers denominate the count
    # threshold, so they are pinned as arithmetic.
    assert auto_block(0.25) == 16
    assert resolve_block(0, 0.25) == 16
    assert resolve_block(24, 0.25) == 24
    assert grid_shape(96, 100, 16) == (6, 7)
