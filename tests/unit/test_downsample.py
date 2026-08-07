"""The first tool's kernel, against arithmetic and against v2's own output.

Downsample was chosen to go first because it can be checked both ways: the
output shape is stated by the parameters, and with anti-aliasing off every
output pixel is a pixel that was in the input at a position you can name. The
arithmetic cases below are v2's, ported to ADR-2's one call shape.

**The goldens are the other half, and they are the mechanism every Phase-4
parity gate reuses.** A checked-in array is only evidence if somebody can
reproduce it, so `REGENERATE` holds the exact command that made the files in
`tests/goldens/` — read out of v2 at `main` rather than out of a worktree that
can hold uncommitted edits, which is the porting discipline's first rule
(`docs/PLAN.md`). Without the command a golden is an array of numbers that
agrees with itself; with it, anyone can re-derive the numbers and find out that
it does not.

Parity is equality, not approximate equality. The tolerance question is a
decision, and the item that minted these goldens did not grant one — an
`INTER_AREA` resample that moved by one count between two builds is exactly the
event this gate exists to surface rather than absorb.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sieve.core.types import ChannelSpec, Frame, FrameSpan
from sieve.tools.downsample import DownsampleParams, run

#: What produced every file in `tests/goldens/`, run from the repo root. The
#: `git diff --quiet` half is not decoration: it is what makes the second half
#: a statement about `main` rather than about whatever is sitting in the sibling
#: worktree, and it exits nonzero — stopping the `&&` — when the two differ.
#:
#: The v2 environment is entered through `--project` rather than by copying the
#: module here, because the kernel imports `sieve.backend.dispatch` and
#: `sieve.core.filter_base`: reproducing it means reproducing v2's package, and
#: pretending otherwise would make the recorded command the one thing in this
#: file nobody had run.
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- "
    "src/sieve/filters/downsample.py src/sieve/core/types.py && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import numpy as np; "
    "from sieve.core.types import ChannelSpec, Frame; "
    "from sieve.filters.downsample import DownsampleParams, downsample_cpu; "
    "f = Frame(data=np.arange(53 * 101, dtype=np.uint16).reshape(53, 101), index=7, "
    "channels=ChannelSpec.GRAY); "
    "[np.save('tests/goldens/downsample_101x53_f4_' + n + '.npy', "
    "downsample_cpu(f, DownsampleParams(factor=4, anti_alias=a)).data) "
    "for n, a in (('area', True), ('stride', False))]\""
)

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"

#: The frame `REGENERATE` builds, restated here rather than loaded, so that a
#: parity failure separates into two readable halves: an input this file and v2
#: agree on by construction, and an output they may not agree on at all.
GOLDEN_WIDTH, GOLDEN_HEIGHT, GOLDEN_FACTOR = 101, 53, 4


def gradient_frame(width: int, height: int) -> Frame:
    """A frame where pixel `(y, x)` holds a value unique to its position."""
    data = np.arange(height * width, dtype=np.uint16).reshape(height, width)
    return Frame(data=data, index=7, channels=ChannelSpec.GRAY)


def one(frame: Frame) -> FrameSpan:
    """A streaming tool's window: the single frame it was handed."""
    return FrameSpan((frame,))


def test_both_paths_agree_on_shape_when_the_factor_does_not_divide() -> None:
    # The one place the two kernel paths could disagree: a stride slice rounds
    # up where an INTER_AREA resize rounds down. If they diverge, `anti_alias`
    # silently changes the output *size* — a parameter documented as changing
    # only pixel values would be changing what every downstream shape check
    # sees.
    frame = gradient_frame(width=101, height=53)

    averaged = run(DownsampleParams(factor=4, anti_alias=True), one(frame), None)
    sampled = run(DownsampleParams(factor=4, anti_alias=False), one(frame), None)

    assert averaged.data.shape == sampled.data.shape == (13, 25)


def test_sampling_takes_the_block_origin_and_averaging_does_not() -> None:
    # What `anti_alias` actually decides, stated as pixels. Sampling is exact
    # and checkable in closed form; averaging is checked as "the block mean",
    # which is the claim the tool's docstring makes to the user.
    frame = gradient_frame(width=8, height=8)

    sampled = run(DownsampleParams(factor=2, anti_alias=False), one(frame), None)
    averaged = run(DownsampleParams(factor=2, anti_alias=True), one(frame), None)

    assert sampled.data[1, 3] == frame.data[2, 6]
    assert averaged.data[1, 3] == pytest.approx(frame.data[2:4, 6:8].mean(), abs=0.5)
    # Identity survives: a tool that renumbered frames would desynchronise every
    # downstream index without changing a pixel, and the executor refuses the
    # node by name when it does.
    assert (sampled.index, sampled.channels) == (frame.index, ChannelSpec.GRAY)


def test_a_factor_that_leaves_nothing_is_refused() -> None:
    # Reachable in practice, not a contrived bound: a replicate's region crop
    # can be a few dozen pixels, and the graph's downsample was set for the full
    # frame. Clamping to 1x1 would let a tuning session proceed against nothing.
    with pytest.raises(ValueError, match="leaves nothing of a 30x20 frame"):
        run(DownsampleParams(factor=32), one(gradient_frame(width=30, height=20)), None)


# v2's fourth case, `test_stored_bytes_prediction_matches_what_the_kernel_
# produced`, is dropped rather than adapted: its subject is `frame_bytes_ratio`,
# which Phase 1 cut with `CostEstimate` because nothing in v3 consumes it
# (`adr/declared-means-verified.md`). It returns with the storage readout.


@pytest.mark.parametrize(
    ("name", "anti_alias"),
    [("area", True), ("stride", False)],
)
def test_output_equals_the_v2_golden(name: str, anti_alias: bool) -> None:
    """v3's kernel reproduces v2's array exactly, on both paths.

    `INTER_AREA` at a non-integer scale — 101 columns into 25 — is the case
    worth pinning: it is an area-weighted resample rather than the block mean
    the parameter's own documentation describes, so a reimplementation that
    read the docstring and wrote the obvious loop would pass every arithmetic
    case above and fail here.
    """
    golden = np.load(GOLDENS / f"downsample_101x53_f4_{name}.npy")
    frame = gradient_frame(width=GOLDEN_WIDTH, height=GOLDEN_HEIGHT)

    produced = run(DownsampleParams(factor=GOLDEN_FACTOR, anti_alias=anti_alias), one(frame), None)

    assert produced.data.dtype == golden.dtype
    assert np.array_equal(produced.data, golden)


def test_the_goldens_are_not_trivially_equal() -> None:
    """Two goldens that happened to be one array would pass parity for nothing."""
    area = np.load(GOLDENS / "downsample_101x53_f4_area.npy")
    stride = np.load(GOLDENS / "downsample_101x53_f4_stride.npy")

    assert not np.array_equal(area, stride)


def test_the_regeneration_command_names_every_golden() -> None:
    """A golden the recorded command does not write is a golden nobody can redo."""
    prefix = "downsample_101x53_f4_"
    unnamed = sorted(
        path.name
        for path in GOLDENS.glob("downsample_*.npy")
        if not path.stem.startswith(prefix) or f"'{path.stem[len(prefix) :]}'" not in REGENERATE
    )

    assert unnamed == []
