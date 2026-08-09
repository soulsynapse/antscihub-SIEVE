"""What only the dense-flow node can get wrong, on `test_block_signal.py`'s framing.

Each case is a distinct lie this tool could tell about a scene. A still arena
that scores nonzero invents motion; a translation whose speed is wrong miscales
every threshold downstream of it; a displacement wider than the expansion
window that reads as a small one is `block_signal.flow_speed` with a slower
kernel, which is the whole reason this tool exists beside it.

There is no parity half. Farneback has no ancestor in v2 — `block_signal` is the
only flow estimator there — so nothing here is cut from a golden and every claim
is a property of the measurement instead. The one that carries the tool's
argument is `test_the_pyramid_measures_a_displacement_wider_than_the_window`:
delete the pyramid and it is the only case that fails.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from sieve.core.tool_base import WarmupKind
from sieve.core.types import ChannelSpec, Frame, FrameCount, FrameSpan
from sieve.tools.farneback import FarnebackParams, FarnebackState, Window
from sieve.tools.farneback import run as farneback_run

FPS = 30.0

#: Wide enough that a 24 px displacement is interior to it, and that the pyramid
#: has something left to look at three levels up.
SIZE = (256, 256)

#: Every median below is taken inside this margin. `np.roll` wraps, so the band
#: it wraps through is a discontinuity no estimator should be judged on, and the
#: expansion at the frame edge is fitted to a neighbourhood partly outside it.
MARGIN = 40

#: The still scene's residual, in px/s. Not zero: unlike `block_signal`, which
#: gates a zero determinant to exactly zero, this tool's stillness is whatever
#: the polynomial solve converges to, and the number below is a bound on the
#: interior rather than an identity.
STILL_INTERIOR_MAX = 1e-3


def textured(sigma: float = 4.0, seed: int = 3) -> NDArray[np.uint8]:
    """A smooth random field at full 8-bit range.

    `block_signal.textured`'s fixture with the rescale that uint8 forces: a
    Gaussian blur of uniform noise collapses toward the mean, and quantizing
    *that* to 8 bits leaves a near-flat frame the solve reads as a fraction of a
    pixel of motion however far it actually moved. The stretch is what keeps
    this a texture rather than a demonstration that quantization loses texture.
    """
    gen = np.random.default_rng(seed)
    rough = gen.uniform(0, 255, SIZE).astype(np.float32)
    smooth = cv2.GaussianBlur(rough, (0, 0), sigma)
    lo, hi = float(smooth.min()), float(smooth.max())
    return np.rint(255.0 * (smooth - lo) / (hi - lo)).astype(np.uint8)


def run_frames(
    frames: list[NDArray[np.uint8]],
    params: FarnebackParams,
    channels: ChannelSpec = ChannelSpec.GRAY,
) -> list[NDArray[np.float32]]:
    """Feed a sequence through one state, the way one execute would."""
    state = FarnebackState()
    out: list[NDArray[np.float32]] = []
    for i, data in enumerate(frames):
        frame = Frame(data=data, index=i, channels=channels)
        out.append(farneback_run(params, FrameSpan((frame,)), state).data)
    return out


def interior(field: NDArray[np.float32]) -> NDArray[np.float32]:
    return field[MARGIN:-MARGIN, MARGIN:-MARGIN]


def translated(field: NDArray[np.uint8], dx: int, dy: int = 0) -> NDArray[np.uint8]:
    return np.roll(np.roll(field, dx, axis=1), dy, axis=0)


def test_the_first_frame_of_a_run_emits_zeros_at_the_inputs_geometry() -> None:
    # There is no displacement across a boundary with nothing on the other
    # side, and the frame that gets emitted for it still has to be a frame:
    # `warmup_frames=1` keeps a requested span off it, and a graph previewing a
    # cold node is handed this one regardless.
    field = textured()
    first = run_frames([field], FarnebackParams(fps=FPS))[0]

    assert first.shape == field.shape
    assert first.dtype == np.float32
    np.testing.assert_array_equal(first, 0.0)


def test_a_still_scene_reads_zero_where_the_estimator_is_not_extrapolating() -> None:
    # The lie this closes is invented motion: a still arena scoring anything
    # reaches `detect` as band power and a count threshold cannot tell it from
    # an animal. Bounded rather than asserted equal, and interior rather than
    # whole-frame — the expansion at the border is fitted over pixels that do
    # not exist, and OpenCV's extrapolation there is not required to cancel.
    still = textured()
    outs = run_frames([still, still, still], FarnebackParams(fps=FPS))

    np.testing.assert_array_equal(outs[0], 0.0)
    for out in outs[1:]:
        assert float(np.abs(interior(out)).max()) < STILL_INTERIOR_MAX


def test_uniform_translation_measures_its_own_speed() -> None:
    # Three pixels per frame at 30 fps is 90 px/s, and the tolerance is the
    # estimator's rather than the arithmetic's. A speed that is merely in the
    # right direction miscales every threshold denominated against it.
    field = textured()
    frames = [translated(field, 3 * i) for i in range(3)]

    speed = run_frames(frames, FarnebackParams(winsize=15, levels=3, fps=FPS))[2]

    assert float(np.median(interior(speed))) == pytest.approx(3.0 * FPS, rel=0.02)


def test_a_diagonal_translation_reads_its_magnitude_not_a_component() -> None:
    # (3, 4) px per frame is 5 px/frame, and the three wrong answers are all
    # nearby: either component alone, and their sum. This is the one case that
    # separates `hypot` from anything that happens to grow with motion.
    field = textured()
    frames = [translated(field, 3 * i, 4 * i) for i in range(2)]

    speed = run_frames(frames, FarnebackParams(winsize=21, levels=3, fps=FPS))[1]

    assert float(np.median(interior(speed))) == pytest.approx(5.0 * FPS, rel=0.02)


def test_the_pyramid_measures_a_displacement_wider_than_the_window() -> None:
    # The tool's whole argument against `block_signal.flow_speed`. The
    # displacement here is 24 px across a 9 px expansion window: a single-scale
    # solve is linearizing over a neighbourhood the scene has entirely left, and
    # it does not merely lose accuracy — it reports a third of the speed, which
    # is a wrong number rather than a missing one. Three levels put 24 px at 3 px
    # on the coarsest, and the estimate comes back.
    field = textured()
    frames = [field, translated(field, 24)]

    def speed(levels: int) -> float:
        out = run_frames(frames, FarnebackParams(winsize=9, levels=levels, fps=FPS))[1]
        return float(np.median(interior(out)))

    assert speed(3) == pytest.approx(24.0 * FPS, rel=0.02)
    assert speed(1) < 0.5 * 24.0 * FPS


def test_fps_is_the_time_base_and_nothing_else() -> None:
    # `fps` is written on the node by whoever configured it and cannot be
    # checked against the container, so what is pinned is that it is a scale and
    # never an input to the estimate: doubling it doubles the array exactly.
    # A node reading a decimated stream is wrong here by the decimation, and
    # that failure is the user's to avoid — `GUIDANCE` says so.
    field = textured()
    frames = [field, translated(field, 3)]

    at_30 = run_frames(frames, FarnebackParams(fps=30.0))[1]
    at_60 = run_frames(frames, FarnebackParams(fps=60.0))[1]

    np.testing.assert_array_equal(at_60, (at_30 * 2.0).astype(np.float32))


def test_a_colour_frame_is_read_through_the_luma_a_gray_one_carries() -> None:
    # `_to_gray` is a channel reduction and not a second estimator: the BGR
    # frame below is a colour encoding of exactly the gray one, so the two runs
    # must be the same array and not merely a close pair.
    field = textured()
    frames = [field, translated(field, 3)]
    colour = [cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR) for frame in frames]

    gray_run = run_frames(frames, FarnebackParams(fps=FPS))[1]
    colour_run = run_frames(colour, FarnebackParams(fps=FPS), ChannelSpec.BGR)[1]

    np.testing.assert_array_equal(colour_run, gray_run)


def test_a_geometry_change_mid_run_is_refused() -> None:
    # The state is the previous frame, and there is no correspondence between
    # two rasters of different sizes to estimate a displacement across. The
    # alternative is OpenCV's own error from inside the solve, which names
    # neither the node nor the frame the geometry changed at.
    field = textured()
    state = FarnebackState()
    params = FarnebackParams(fps=FPS)
    farneback_run(
        params, FrameSpan((Frame(data=field, index=0, channels=ChannelSpec.GRAY),)), state
    )

    smaller = Frame(data=field[:128, :128], index=1, channels=ChannelSpec.GRAY)
    with pytest.raises(ValueError, match="one run is one geometry"):
        farneback_run(params, FrameSpan((smaller,)), state)


def test_both_weightings_measure_one_field_which_is_why_there_is_one_emission() -> None:
    # `window` is `downsample`'s area-vs-stride: two ways of weighting one
    # neighbourhood, agreeing on the displacement and differing in the arrays
    # they arrive at it through. If they disagreed on the speed they would be
    # two products and the spec would owe a second emission
    # (`adr/declared-means-verified.md`).
    field = textured()
    frames = [field, translated(field, 3)]

    box = run_frames(frames, FarnebackParams(window=Window.BOX, winsize=21, fps=FPS))[1]
    gaussian = run_frames(frames, FarnebackParams(window=Window.GAUSSIAN, winsize=21, fps=FPS))[1]

    assert float(np.median(interior(gaussian))) == pytest.approx(
        float(np.median(interior(box))), rel=0.02
    )
    assert not np.array_equal(box, gaussian)


def test_the_warmup_is_the_previous_frame_and_settles_exactly() -> None:
    # `block_signal`'s declaration, for its reason: two frames decide every
    # value, so the executor may re-settle one frame of state and serve the
    # rest (`adr/cache-admission-is-bounded-warmup.md`). The bound is a
    # constant at every setting, which is what `max_warmup_frames` states.
    spec = FarnebackParams.spec()

    assert spec.warmup_frames == FrameCount(1)
    assert spec.warmup_kind is WarmupKind.BOUNDED
    assert spec.settling_epsilon == 0.0
    assert spec.stateful
    assert FarnebackParams.max_warmup_frames() == FrameCount(1)


def test_every_window_has_a_declared_presentation_label() -> None:
    # The enum is discovered from the tool and the labels live on the spec
    # channel a front end reads, so a weighting the kernel accepts but cannot
    # name fails in the declaration rather than in a widget map.
    labels = FarnebackParams.spec().param_value_labels["window"]

    assert set(labels) == {w.value for w in Window}
    assert all(label for label in labels.values())
