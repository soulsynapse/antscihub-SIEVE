"""Two tools' kernels, against arithmetic and against v2's own arrays.

The pairing is v2's and ports as-is: `rescale` and `normalize` were covered by
one file there, and they are the two halves of the same preprocessing step —
how much frame reaches the detector, and on what contrast scale its values sit.

The goldens follow `test_downsample.py`'s mechanism, `REGENERATE` and all, and
the reasoning there about equality-not-approximation applies unchanged. What is
new here is *which* case is worth a golden. For `rescale` it is the same
non-integer `INTER_AREA` scale — 101 columns into 25. For `normalize` it is the
BGR frame: the arithmetic case below pins that the gray projection of the output
lands on mean 128 and sd 32, which is the claim v2's module docstring argues,
and the golden pins the float32 array that claim was satisfied by, so a
reimplementation that pooled the channels and then happened to satisfy the gray
check by construction still has to produce v2's numbers.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

from sieve.core.types import ChannelSpec, Frame, FrameSpan
from sieve.tools.normalize import NormalizeMode, NormalizeParams
from sieve.tools.normalize import run as normalize_run
from sieve.tools.rescale import RescaleParams
from sieve.tools.rescale import run as rescale_run

#: What produced this file's goldens, run from the repo root. `git diff --quiet`
#: is what makes the rest a statement about v2's `main` rather than about
#: whatever is sitting in the sibling worktree; it exits nonzero and stops the
#: `&&` when the two differ. `--project` enters v2's environment rather than
#: copying its kernels here, because both import `sieve.backend.dispatch` and
#: `sieve.core.filter_base` — reproducing the array means reproducing v2's
#: package.
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- "
    "src/sieve/filters/rescale.py src/sieve/filters/normalize.py "
    "src/sieve/core/types.py && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import numpy as np; "
    "from sieve.core.types import ChannelSpec, Frame; "
    "from sieve.filters.rescale import RescaleParams, rescale_cpu; "
    "from sieve.filters.normalize import NormalizeMode, NormalizeParams, normalize_cpu; "
    "z = NormalizeParams(mode=NormalizeMode.ZSCORE); "
    "g = Frame(data=np.arange(53 * 101, dtype=np.uint16).reshape(53, 101), index=7, "
    "channels=ChannelSpec.GRAY); "
    "r = np.arange(48 * 48, dtype=np.float32).reshape(48, 48); "
    "c = Frame(data=np.stack([r * 0.1 + 40, r * 0.3 + 120, r * 0.05 + 200], axis=-1)"
    ".astype(np.float32), index=0, channels=ChannelSpec.BGR); "
    "np.save('tests/goldens/rescale_101x53_s025.npy', "
    "rescale_cpu(g, RescaleParams(scale=0.25)).data); "
    "np.save('tests/goldens/normalize_101x53_zscore_gray.npy', normalize_cpu(g, z).data); "
    "np.save('tests/goldens/normalize_48x48_zscore_bgr.npy', normalize_cpu(c, z).data)\""
)

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"


def gradient_frame(width: int, height: int) -> Frame:
    """A frame where pixel `(y, x)` holds a value unique to its position."""
    data = np.arange(height * width, dtype=np.uint16).reshape(height, width)
    return Frame(data=data, index=7, channels=ChannelSpec.GRAY)


def banded_ramp() -> NDArray[np.float32]:
    """Three planes with deliberately different means and different slopes.

    Different slopes and not merely different means, because the two channel
    orders have to disagree on the spread as well as on the centre: a fixture
    that only moved the mean would let a wrong projection still land on sd 32.
    """
    ramp = np.arange(48 * 48, dtype=np.float32).reshape(48, 48)
    return np.stack([ramp * 0.1 + 40, ramp * 0.3 + 120, ramp * 0.05 + 200], axis=-1).astype(
        np.float32
    )


def banded_bgr_frame() -> Frame:
    """A color frame whose channels have deliberately different means.

    Pooled-channel statistics and gray-projection statistics disagree on this
    frame, which is the only condition under which a test can tell the two
    implementations apart.
    """
    return Frame(data=banded_ramp(), index=0, channels=ChannelSpec.BGR)


def one(frame: Frame) -> FrameSpan:
    """A streaming tool's window: the single frame it was handed."""
    return FrameSpan((frame,))


def test_rescale_rounds_each_extent_and_preserves_dtype() -> None:
    # The parity semantic: `round(src x scale)` per axis, not floor and not a
    # shared factor — 101 x 0.25 is 25, 53 x 0.25 is 13. And dtype survives,
    # because a resize that widened uint16 to float would change what every
    # downstream declaration admits.
    frame = gradient_frame(width=101, height=53)

    out = rescale_run(RescaleParams(scale=0.25), one(frame), None)

    assert out.data.shape == (13, 25)
    assert out.data.dtype == np.uint16
    assert (out.index, out.channels) == (7, ChannelSpec.GRAY)


def test_rescale_rounds_up_past_the_half() -> None:
    # The case that separates `round` from `int`, which no other fixture here
    # does: 101 and 53 at 0.25 both land under the half, and 12 x 8 at 0.05
    # lands where `max(1, ...)` covers the disagreement. 6 x 0.45 is 2.7, so
    # rounding gives 3 and truncation gives 2.
    frame = gradient_frame(width=6, height=6)

    out = rescale_run(RescaleParams(scale=0.45), one(frame), None)

    assert out.data.shape == (3, 3)


def test_rescale_at_one_is_the_identity_object() -> None:
    # Not merely equal pixels: the same frame object, because the no-op path
    # exists to cost nothing and a copy per frame is not nothing.
    frame = gradient_frame(width=10, height=10)

    assert rescale_run(RescaleParams(scale=1.0), one(frame), None) is frame


def test_rescale_keeps_an_axis_a_tiny_crop_would_have_lost() -> None:
    # `downsample` refuses this case and `rescale` floors it to one pixel, and
    # the split is not an inconsistency: an integer factor that exceeds an
    # extent is a graph configured for a frame it is not being shown, while a
    # float scale legitimately rests anywhere in its range and a replicate's
    # region is what shrinks underneath it.
    frame = gradient_frame(width=12, height=8)

    out = rescale_run(RescaleParams(scale=0.05), one(frame), None)

    assert out.data.shape == (1, 1)


def test_zscore_hits_target_mean_and_sd() -> None:
    # The core claim: a nonconstant frame lands on mean 128, sd 32, float32.
    frame = gradient_frame(width=64, height=64)

    out = normalize_run(NormalizeParams(mode=NormalizeMode.ZSCORE), one(frame), None)

    assert out.data.dtype == np.float32
    assert float(out.data.mean()) == pytest.approx(128.0, abs=0.01)
    assert float(out.data.std()) == pytest.approx(32.0, abs=0.01)


def test_normalize_off_is_the_identity_object() -> None:
    # `rescale` at 1.0 on the value axis, and the same reason: "no
    # normalization" is a setting of the parameter, not the absence of a node,
    # so it has to cost what the absence would.
    frame = gradient_frame(width=10, height=10)

    assert normalize_run(NormalizeParams(mode=NormalizeMode.OFF), one(frame), None) is frame


def test_zscore_of_a_constant_frame_centers_without_dividing() -> None:
    # A black lead-in frame must not become NaN that poisons every block
    # series downstream — v1's guard, kept exactly.
    frame = Frame(data=np.full((32, 32), 7.0, np.float32), index=0, channels=ChannelSpec.GRAY)

    out = normalize_run(NormalizeParams(mode=NormalizeMode.ZSCORE), one(frame), None)

    assert np.isfinite(out.data).all()
    np.testing.assert_allclose(out.data, 0.0, atol=1e-5)


def test_zscore_on_bgr_normalizes_the_downstream_gray_series() -> None:
    # The design decision the module docstring argues: statistics come from
    # the gray projection so the series a downstream detector sees is exactly
    # v1's normalized gray. The pin is on the *projection of the output*, not
    # the output itself — pooled-channel statistics would pass a naive
    # mean/std check on the array and still break parity.
    frame = banded_bgr_frame()

    out = normalize_run(NormalizeParams(mode=NormalizeMode.ZSCORE), one(frame), None)

    gray = cv2.cvtColor(out.data, cv2.COLOR_BGR2GRAY)
    assert float(gray.mean()) == pytest.approx(128.0, abs=0.05)
    assert float(gray.std()) == pytest.approx(32.0, abs=0.05)


def test_zscore_on_rgb_reads_the_channels_in_their_declared_order() -> None:
    # `_gray_stats` branches on the layout, and BT.601 is not symmetric: the
    # same three planes weight to 0.2025 per ramp step read as BGR and 0.2117
    # read as RGB, so a projection hard-wired to one order misses sd 32 by
    # about 1.5 on the other. The BGR case above cannot see that branch.
    frame = Frame(data=banded_ramp(), index=0, channels=ChannelSpec.RGB)

    out = normalize_run(NormalizeParams(mode=NormalizeMode.ZSCORE), one(frame), None)

    gray = cv2.cvtColor(out.data, cv2.COLOR_RGB2GRAY)
    assert float(gray.mean()) == pytest.approx(128.0, abs=0.05)
    assert float(gray.std()) == pytest.approx(32.0, abs=0.05)


def test_normalize_carries_the_frame_index() -> None:
    # Which frame this is survives the value axis. `rescale` is asserted on the
    # same point; a tool that renumbered would misalign every series a
    # downstream detector indexes by frame.
    frame = gradient_frame(width=16, height=16)

    out = normalize_run(NormalizeParams(mode=NormalizeMode.ZSCORE), one(frame), None)

    assert (out.index, out.channels) == (7, ChannelSpec.GRAY)


def test_rescale_output_equals_the_v2_golden() -> None:
    """v3's kernel reproduces v2's array exactly at a non-integer scale.

    101 columns into 25 is the case worth pinning for `downsample`'s reason:
    `INTER_AREA` there is an area-weighted resample rather than the block mean
    the parameter reads as, so an implementation written from the description
    passes every shape case above and fails here.
    """
    golden = np.load(GOLDENS / "rescale_101x53_s025.npy")
    frame = gradient_frame(width=101, height=53)

    produced = rescale_run(RescaleParams(scale=0.25), one(frame), None)

    assert produced.data.dtype == golden.dtype
    assert np.array_equal(produced.data, golden)


@pytest.mark.parametrize(
    ("name", "frame_of"),
    [
        ("101x53_zscore_gray", lambda: gradient_frame(width=101, height=53)),
        ("48x48_zscore_bgr", banded_bgr_frame),
    ],
)
def test_normalize_output_equals_the_v2_golden(name: str, frame_of: object) -> None:
    """v3's kernel reproduces v2's array exactly, on gray and on color.

    Equality rather than a tolerance, as everywhere else in the Phase-4 gate,
    and here it is doing specific work: the fused affine v1 measured at 2.3-3x
    is `g * a + b` with `a = 32 / std`, and the four-temporary spelling it
    replaced differs from it in the last bits of float32. A kernel that
    "simplified" back to `(g - mean) / std * 32 + 128` would satisfy every
    `approx` above and fail this.
    """
    golden = np.load(GOLDENS / f"normalize_{name}.npy")
    frame = frame_of()  # type: ignore[operator]

    produced = normalize_run(NormalizeParams(mode=NormalizeMode.ZSCORE), one(frame), None)

    assert produced.data.dtype == golden.dtype
    assert np.array_equal(produced.data, golden)


def test_the_goldens_are_not_trivially_equal() -> None:
    """Two goldens that happened to be one array would pass parity for nothing."""
    gray = np.load(GOLDENS / "normalize_101x53_zscore_gray.npy")
    rescaled = np.load(GOLDENS / "rescale_101x53_s025.npy")

    assert gray.shape != rescaled.shape


def test_the_regeneration_command_names_every_golden() -> None:
    """A golden the recorded command does not write is a golden nobody can redo."""
    unnamed = sorted(
        path.name
        for path in GOLDENS.glob("*.npy")
        if path.stem.startswith(("rescale_", "normalize_")) and path.name not in REGENERATE
    )

    assert unnamed == []
