"""The crop kernel: the identity value, the trim, and whose pixels the box is in.

Each test here stands for a way the crop stops being a filter. The identity crop
is what keeps `ROI | None` out of the plan, so a default that is not the whole
frame is the rule broken rather than a wrong pixel. The coordinate space is the
migration's named risk (`docs/todo/the-crop-is-a-filter.md`): a box read in the
wrong numbering produces a frame that looks entirely plausible.
"""

from __future__ import annotations

import numpy as np

from sieve.core.types import ROI, ChannelSpec, Frame
from sieve.filters.crop import CropParams, crop_cpu


def gradient_frame(width: int, height: int) -> Frame:
    """A frame where pixel `(y, x)` holds a value unique to its position."""
    data = np.arange(height * width, dtype=np.uint16).reshape(height, width)
    return Frame(data=data, index=7, channels=ChannelSpec.GRAY)


def test_the_identity_crop_is_the_whole_frame_at_any_size() -> None:
    # What "no crop" is spelled as. Two shapes, and neither of them square,
    # because a default that happened to be one frame's dimensions would pass
    # the first assertion and fail the second — and a default written as a
    # pixel box is exactly the thing the unbounded region exists to avoid.
    for width, height in ((160, 120), (37, 53)):
        frame = gradient_frame(width=width, height=height)

        cropped = crop_cpu(frame, CropParams())

        assert np.array_equal(cropped.data, frame.data)
        assert (cropped.index, cropped.channels) == (frame.index, ChannelSpec.GRAY)


def test_a_region_overhanging_the_frame_is_trimmed_rather_than_refused() -> None:
    # The same clamp `executor._crop` applies, which is what makes the identity
    # value expressible at all: an unbounded region is only "the whole frame"
    # because a region that does not fit comes back as the part that does.
    frame = gradient_frame(width=20, height=10)

    cropped = crop_cpu(frame, CropParams(roi=ROI(x=16, y=8, width=64, height=48)))

    assert cropped.data.shape == (2, 4)
    assert np.array_equal(cropped.data, frame.data[8:10, 16:20])


def test_a_second_crop_is_denominated_in_the_first_s_output() -> None:
    # The migration's named risk. `ROI`'s docstring says source pixels because
    # it was written for `Replicate.roi`; this filter's box indexes whatever
    # frame arrives at it. Composed, the offsets add — and a kernel that had
    # kept the source numbering would return `frame.data[3:5, 4:8]` here, which
    # is a region of the right size in the wrong place.
    frame = gradient_frame(width=20, height=10)
    outer = ROI(x=4, y=3, width=12, height=6)
    inner = ROI(x=4, y=3, width=4, height=2)

    once = crop_cpu(frame, CropParams(roi=outer))
    twice = crop_cpu(once, CropParams(roi=inner))

    assert np.array_equal(twice.data, frame.data[6:8, 8:12])


def test_the_crop_does_not_hold_the_frame_it_came_from() -> None:
    # A slice would keep the whole input alive, so a cached crop node would
    # retain one decoded frame per stored entry — the point of cropping,
    # defeated silently and only visible as memory. `executor._crop` returns
    # the view because its result is consumed and dropped within the loop.
    frame = gradient_frame(width=20, height=10)

    cropped = crop_cpu(frame, CropParams(roi=ROI(x=4, y=3, width=12, height=6)))

    assert not np.shares_memory(cropped.data, frame.data)


def test_the_identity_crop_is_a_value_in_the_saved_params() -> None:
    # `X | None` never reaches the plan (REWORK.md R1), so the default has to
    # survive to the cache key as a region rather than as an absence. A field
    # that serialized to null would take this with it.
    canonical = CropParams().canonical_json()

    assert canonical == '{"roi":{"height":1048576,"width":1048576,"x":0,"y":0}}'
    assert CropParams.model_validate_json(CropParams().model_dump_json()) == CropParams()
