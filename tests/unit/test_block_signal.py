"""The four block signals: the claims that make each of them trustworthy.

Ported from v2's file of the same name, whose framing carries: each failure is a
distinct lie the node could tell — a static scene that scores nonzero invents
motion, a translation whose speed is wrong miscales every threshold, and an
aperture-degenerate block that reports noise instead of zero turns
"unmeasurable" into "event".

What is new is the parity half, on 03.7's mechanism. One golden per signal,
because the four are four code paths that share only the reduction: change
energy is one blur, flow speed is the five-product LK solve, coherence is the
six-product block tensor and its eigensolve, and flow agreement is the circular
mean over the pixels the solve resolved. A single golden would pin one of them
and leave the other three to the inequalities above, which are satisfiable by
arithmetic that is merely in the right direction.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

import sieve.tools.block_signal as block_signal_module
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.tools.block_signal import (
    BlockSignalParams,
    BlockSignalState,
    Signal,
    auto_block,
    grid_shape,
    resolve_block,
)
from sieve.tools.block_signal import run as block_signal_run

FPS = 30.0
RAGGED_BLOCK_MEAN_MAX_DELTA = 3.0517578125e-05
BlockMean = Callable[[NDArray[np.float32], int, int, int], NDArray[np.float32]]
block_mean = cast(BlockMean, vars(block_signal_module)["_block_mean"])

#: The one naming scheme the command below writes and this file reads. Named
#: rather than spelled twice, so `test_the_regeneration_command_names_every_golden`
#: compares the checked-in set against the command instead of against a second
#: copy of the scheme.
GOLDEN_PREFIX = "block_signal_96x96_b16_"

#: The block size every golden was cut at. A golden regenerated under a
#: different one would still load and still compare, so the number lives in one
#: place the command and the parity case both read.
GOLDEN_BLOCK = 16

#: What produced this file's goldens, run from the repo root, on
#: `test_rescale_normalize.py`'s mechanism and for its reason: `git diff --quiet`
#: is what makes the arrays a statement about v2's `main` rather than about
#: whatever sits in the sibling worktree, and `--project` enters v2's environment
#: because reproducing the array means reproducing v2's package.
#:
#: The texture is `textured()` below, spelled out rather than imported — the
#: regenerating process has v2's `sieve` on its path and not this one's, and a
#: fixture the command builds differently from the test is a golden that pins a
#: frame nothing here ever produces.
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- "
    "src/sieve/filters/block_signal.py src/sieve/core/types.py && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import cv2, numpy as np; "
    "from sieve.core.types import ChannelSpec, Frame; "
    "from sieve.filters.block_signal import BlockSignalParams, BlockSignalState, Signal, "
    "block_signal_cpu; "
    "t = cv2.GaussianBlur(np.random.default_rng(3).uniform(0, 255, (96, 96))"
    ".astype(np.float32), (0, 0), 3.0); "
    "frames = [np.roll(t, i, axis=1) for i in range(2)]; "
    "last = lambda p: [block_signal_cpu(Frame(data=d, index=i, channels=ChannelSpec.GRAY), p, st)"
    ".data for st in [BlockSignalState()] for i, d in enumerate(frames)][-1]; "
    f"[np.save('tests/goldens/{GOLDEN_PREFIX}' + g.value + '.npy', "
    f'last(BlockSignalParams(signal=g, block={GOLDEN_BLOCK}, fps=30.0))) for g in Signal]"'
)

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"


def run_frames(
    frames: list[NDArray[np.float32]], params: BlockSignalParams
) -> list[NDArray[np.float32]]:
    """Feed a sequence through one state, the way one execute would."""
    state = BlockSignalState()
    out: list[NDArray[np.float32]] = []
    for i, data in enumerate(frames):
        frame = Frame(data=data, index=i, channels=ChannelSpec.GRAY)
        out.append(block_signal_run(params, FrameSpan((frame,)), state).data)
    return out


def textured() -> NDArray[np.float32]:
    """A smooth random field: enough 2-D texture that LK is well-posed."""
    gen = np.random.default_rng(3)
    rough = gen.uniform(0, 255, (96, 96)).astype(np.float32)
    return cast(NDArray[np.float32], cv2.GaussianBlur(rough, (0, 0), 3.0))


def nan_padded_block_mean(field: NDArray[np.float32], block: int) -> NDArray[np.float32]:
    """The previous ragged reducer, kept as an oracle."""
    h, w = field.shape
    ny, nx = grid_shape(h, w, block)
    padded = np.pad(
        field.astype(np.float32, copy=False),
        ((0, ny * block - h), (0, nx * block - w)),
        constant_values=np.nan,
    )
    cells = padded.reshape(ny, block, nx, block).transpose(0, 2, 1, 3)
    return np.nanmean(cells.reshape(ny, nx, block * block), axis=2).astype(np.float32)


def test_ragged_block_mean_matches_the_padded_oracle_with_float32_delta() -> None:
    field = np.random.default_rng(456).uniform(0.0, 255.0, (349, 321)).astype(np.float32)
    block = 64
    h, w = field.shape
    ny, nx = grid_shape(h, w, block)

    old = nan_padded_block_mean(field, block)
    new = block_mean(field, block, ny, nx)
    delta = np.abs(new - old)

    assert new.shape == (6, 6)
    assert float(delta.max()) <= float(RAGGED_BLOCK_MEAN_MAX_DELTA)
    np.testing.assert_allclose(new, old, rtol=0.0, atol=RAGGED_BLOCK_MEAN_MAX_DELTA)


def test_ragged_block_mean_keeps_nan_skipping_semantics() -> None:
    field = np.arange(17 * 19, dtype=np.float32).reshape(17, 19)
    field[3, 4] = np.nan
    field[15, 18] = np.nan
    block = 8
    h, w = field.shape
    ny, nx = grid_shape(h, w, block)

    old = nan_padded_block_mean(field, block)
    new = block_mean(field, block, ny, nx)

    np.testing.assert_array_equal(new, old)


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
    # confident 1.
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
    # The enum is discovered from the tool and the labels live on the same spec
    # presentation channel a front end reads. A signal the kernel computes but
    # cannot name now fails in the tool's declaration, not in a widget map.
    labels = BlockSignalParams.spec().param_value_labels["signal"]

    assert set(labels) == {s.value for s in Signal}
    assert all(label for label in labels.values())


def test_warmup_is_the_previous_frame_and_settles_exactly() -> None:
    spec = BlockSignalParams.spec()

    assert spec.warmup_frames == FrameCount(1)
    assert spec.settling_epsilon == 0.0


def test_block_resolution_is_the_one_source_of_grid_truth() -> None:
    # auto = 64 source px at scale; explicit block wins; the grid ceils so
    # ragged edges are real blocks. These three numbers denominate the count
    # threshold, so they are pinned as arithmetic.
    assert auto_block(0.25) == 16
    assert resolve_block(0, 0.25) == 16
    assert resolve_block(24, 0.25) == 24
    assert grid_shape(96, 100, 16) == (6, 7)


@pytest.mark.parametrize("signal", list(Signal))
def test_each_signal_reproduces_the_v2_golden(signal: Signal) -> None:
    """v3's kernel reproduces v2's array exactly, on all four signals.

    Equality rather than a tolerance, as everywhere else in the Phase-4 gate.
    The frame pair is a one-pixel translation of the textured field, which is
    the only fixture in this file that all four signals answer non-trivially:
    the static case is zero everywhere by construction and the aperture case is
    zero for two of the four, so a golden cut from either would pin nothing.
    """
    golden = np.load(GOLDENS / f"{GOLDEN_PREFIX}{signal.value}.npy")
    field = textured()
    frames = [np.roll(field, i, axis=1) for i in range(2)]

    produced = run_frames(frames, BlockSignalParams(signal=signal, block=GOLDEN_BLOCK, fps=FPS))[1]

    assert produced.dtype == golden.dtype
    assert np.array_equal(produced, golden)


def test_the_goldens_are_four_different_arrays() -> None:
    """Four signals that happened to be one array would pass parity for nothing.

    `change_energy` is the one that could not be confused with the others by
    accident — it is unbounded px^2 while the two ratios live in [0, 1] — so the
    comparison that earns its place is between every pair.
    """
    arrays = [np.load(GOLDENS / f"{GOLDEN_PREFIX}{s.value}.npy") for s in Signal]

    for i, left in enumerate(arrays):
        for right in arrays[i + 1 :]:
            assert not np.array_equal(left, right)


def test_the_regeneration_command_names_every_golden() -> None:
    """A golden the recorded command does not write is a golden nobody can redo.

    The command composes its names from `GOLDEN_PREFIX` and the signal values,
    so the check is that the scheme is the one recorded and that the checked-in
    set is exactly what it produces — no golden outside it, and none missing.
    """
    assert GOLDEN_PREFIX in REGENERATE
    assert "for g in Signal" in REGENERATE

    written = sorted(path.name for path in GOLDENS.glob(f"{GOLDEN_PREFIX}*.npy"))
    assert written == sorted(f"{GOLDEN_PREFIX}{s.value}.npy" for s in Signal)
    assert f"block={GOLDEN_BLOCK}" in REGENERATE.replace(" ", "")
