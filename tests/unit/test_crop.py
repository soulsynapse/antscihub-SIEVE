"""The crop kernel: the identity value, the trim, and whose pixels the box is in.

Each case here stands for a way the crop stops being a tool. The identity crop
is what keeps `ROI | None` out of the plan, so a default that is not the whole
frame is a rule broken rather than a wrong pixel. The coordinate space is the
one that fails quietly: a box read in the wrong numbering returns a region of
the right size in the wrong place, and the frame it produces looks entirely
plausible.

The goldens reuse 03.7's mechanism — `REGENERATE` below holds the command that
made the files in `tests/goldens/`, read out of v2 at `main`. Both cases are
clamps, because a slice is where v3 and v2 cannot differ and the clamp is where
they could: `ROI.clamped_to` pins a region that has walked off the frame to the
last legal pixel rather than returning nothing, and a reimplementation that
treated an out-of-frame region as empty would pass every arithmetic case below.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from sieve.core.tool_base import ParamStereotype
from sieve.core.types import ROI, ChannelSpec, Frame, FrameSpan
from sieve.tools.crop import WHOLE_FRAME_EXTENT, CropParams, run

#: What produced `tests/goldens/crop_101x53_*.npy`, run from the repo root. The
#: `git diff --quiet` half makes the second half a statement about `main` rather
#: than about whatever is sitting in the sibling worktree, and it exits nonzero
#: — stopping the `&&` — when the two differ.
REGENERATE = (
    "git -C ../antscihub-SIEVE-v2 diff --quiet main -- "
    "src/sieve/filters/crop.py src/sieve/core/types.py && "
    'uv run --project ../antscihub-SIEVE-v2 python -c "'
    "import numpy as np; "
    "from sieve.core.types import ROI, ChannelSpec, Frame; "
    "from sieve.filters.crop import CropParams, crop_cpu; "
    "f = Frame(data=np.arange(53 * 101, dtype=np.uint16).reshape(53, 101), index=7, "
    "channels=ChannelSpec.GRAY); "
    "[np.save('tests/goldens/crop_101x53_' + n + '.npy', "
    "crop_cpu(f, CropParams(roi=ROI(x=x, y=y, width=w, height=h))).data) "
    "for n, (x, y, w, h) in "
    "(('clamped', (90, 48, 64, 48)), ('outside', (200, 100, 8, 8)))]\""
)

GOLDENS = Path(__file__).resolve().parents[1] / "goldens"

#: The frame `REGENERATE` builds and the two regions it crops it with, restated
#: rather than loaded, so a parity failure separates into an input this file and
#: v2 agree on by construction and an output they may not agree on at all.
GOLDEN_WIDTH, GOLDEN_HEIGHT = 101, 53
GOLDEN_REGIONS = {
    "clamped": ROI(x=90, y=48, width=64, height=48),
    "outside": ROI(x=200, y=100, width=8, height=8),
}


def gradient_frame(width: int, height: int) -> Frame:
    """A frame where pixel `(y, x)` holds a value unique to its position."""
    data = np.arange(height * width, dtype=np.uint16).reshape(height, width)
    return Frame(data=data, index=7, channels=ChannelSpec.GRAY)


def one(frame: Frame) -> FrameSpan:
    """A streaming tool's window: the single frame it was handed."""
    return FrameSpan((frame,))


def test_the_identity_crop_is_the_whole_frame_at_any_size() -> None:
    # What "no crop" is spelled as. Two shapes, neither square, because a
    # default that happened to be one frame's dimensions would pass the first
    # iteration and fail the second — and a default written as a pixel box is
    # exactly what the unbounded region exists to avoid.
    for width, height in ((160, 120), (37, 53)):
        frame = gradient_frame(width=width, height=height)

        cropped = run(CropParams(), one(frame), None)

        assert np.array_equal(cropped.data, frame.data)
        assert (cropped.index, cropped.channels) == (frame.index, ChannelSpec.GRAY)


def test_a_region_overhanging_the_frame_is_trimmed_rather_than_refused() -> None:
    # The clamp is what makes the identity value expressible at all: an
    # unbounded region is only "the whole frame" because a region that does not
    # fit comes back as the part that does.
    frame = gradient_frame(width=20, height=10)

    cropped = run(CropParams(region=ROI(x=16, y=8, width=64, height=48)), one(frame), None)

    assert cropped.data.shape == (2, 4)
    assert np.array_equal(cropped.data, frame.data[8:10, 16:20])


def test_a_second_crop_is_denominated_in_the_first_s_output() -> None:
    # The quiet failure. `ROI` names no coordinate space, and the space this
    # tool's region indexes is whatever frame arrives at the node. Composed, the
    # offsets add — a kernel that had kept the source numbering would return
    # `frame.data[3:5, 4:8]` here, which is the right size in the wrong place.
    frame = gradient_frame(width=20, height=10)

    once = run(CropParams(region=ROI(x=4, y=3, width=12, height=6)), one(frame), None)
    twice = run(CropParams(region=ROI(x=4, y=3, width=4, height=2)), one(once), None)

    assert np.array_equal(twice.data, frame.data[6:8, 8:12])


def test_the_crop_does_not_hold_the_frame_it_came_from() -> None:
    # A slice would keep the whole input alive, so a cached crop node would
    # retain one decoded frame per stored entry — the point of cropping,
    # defeated silently and visible only as memory.
    frame = gradient_frame(width=20, height=10)

    cropped = run(CropParams(region=ROI(x=4, y=3, width=12, height=6)), one(frame), None)

    assert not np.shares_memory(cropped.data, frame.data)


def test_the_identity_crop_is_a_value_in_the_saved_params() -> None:
    # The default has to survive to the cache key as a region rather than as an
    # absence; a field that serialized to null would take this with it. The
    # extent is asserted literally because it is the number a reader meets in a
    # saved document, and a changed bound silently re-keys every crop node.
    canonical = CropParams().canonical_json()

    assert canonical == '{"region":{"height":1048576,"width":1048576,"x":0,"y":0}}'
    assert WHOLE_FRAME_EXTENT == 1048576
    assert CropParams.model_validate_json(CropParams().model_dump_json()) == CropParams()


def test_the_region_declares_the_stereotype_the_canvas_handoff_reads() -> None:
    # The GUI reaches a crop through the kind, never through `tool_id`
    # (`adr/gui-knows-kinds-not-tools.md`), so an undeclared region is a
    # parameter Phase 7's generator has no surface for.
    assert CropParams.spec().param_stereotypes["region"] is ParamStereotype.REGION


def test_the_clamped_region_equals_the_v2_golden() -> None:
    """v3 reproduces v2's array for a box hanging off the bottom-right corner."""
    golden = np.load(GOLDENS / "crop_101x53_clamped.npy")
    frame = gradient_frame(width=GOLDEN_WIDTH, height=GOLDEN_HEIGHT)

    produced = run(CropParams(region=GOLDEN_REGIONS["clamped"]), one(frame), None)

    assert produced.data.dtype == golden.dtype
    assert np.array_equal(produced.data, golden)


def test_a_region_entirely_outside_the_frame_equals_the_v2_golden() -> None:
    """The degenerate clamp, which is the one worth pinning against v2.

    Both the origin and the extent are past the frame, so `clamped_to` pins the
    region to the last legal pixel and floors it at one pixel each way. The
    result is a 1x1 frame rather than an empty array or a raise, and every
    downstream shape check depends on which of those three it is.
    """
    golden = np.load(GOLDENS / "crop_101x53_outside.npy")
    frame = gradient_frame(width=GOLDEN_WIDTH, height=GOLDEN_HEIGHT)

    produced = run(CropParams(region=GOLDEN_REGIONS["outside"]), one(frame), None)

    assert produced.data.shape == (1, 1)
    assert np.array_equal(produced.data, golden)


def test_neither_golden_is_the_frame_it_was_cut_from() -> None:
    """A golden regenerated with the region dropped would pass parity for nothing."""
    for name in GOLDEN_REGIONS:
        golden = np.load(GOLDENS / f"crop_101x53_{name}.npy")

        assert golden.size < GOLDEN_HEIGHT * GOLDEN_WIDTH


def test_the_regeneration_command_names_every_golden() -> None:
    """A golden the recorded command does not write is a golden nobody can redo."""
    prefix = "crop_101x53_"
    unnamed = sorted(
        path.name
        for path in GOLDENS.glob("crop_*.npy")
        if not path.stem.startswith(prefix) or f"'{path.stem[len(prefix) :]}'" not in REGENERATE
    )

    assert unnamed == []
