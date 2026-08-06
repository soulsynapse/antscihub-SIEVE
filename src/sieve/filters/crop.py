"""Take a region of every frame, with the whole frame as the identity value.

REWORK.md R1's cheapest proof: the crop was already `Frame -> Frame`,
`Mode.STREAMING`, and needed no extension of the kernel protocol — it was simply
living in `pipeline/executor.py` as `_crop`, applied from `plan.roi`, where no
cache key could see it and no graph could place it. This module is the same
operation declared as a filter, discovered like every other.

**The region is denominated in this filter's *input* space, not in source
pixels.** `ROI`'s own docstring is written for `Replicate.roi`, which indexes
the decoded source frame; a crop node placed after a `rescale` indexes the
rescaled frame, and there is nothing here that could convert between the two.
That is the migration's named risk (`docs/todo/the-crop-is-a-filter.md`) stated
where the parameter is declared: whoever synthesizes a crop node from a
replicate's box must put it at the *root*, where the two spaces coincide.
`test_crop.py::test_a_second_crop_is_denominated_in_the_first_s_output` is what
fails if anything starts assuming otherwise.

**"No crop" is `WHOLE_FRAME`, never `None`.** The identity of a present
parameter, so no `X | None` propagates through the plan (R1's
identity-is-not-exemption clause). The extent is unbounded rather than the
frame's own, because a full-frame ROI in pixels cannot be written by anything
that does not know the frame size — and the two writers that will need it
cannot: `Project` records no source dimensions, so the schema-v6 upgrade
validator (`docs/todo/the-graph-carries-the-crop-the-span-and-the-detector.md`)
synthesizes nodes from a document alone, and a hand-written YAML is typed
without opening the video. An unbounded region clamps to exactly the frame it
meets, which makes "the whole of it" a value both of them can write.

The operation is therefore the *intersection* of the declared region with the
frame, which is also what `executor._crop` has always done — clamping there was
argued from a reader that returns a smaller frame than the ROI was drawn
against, and the same clamp is what makes the identity value expressible here.
Both go through `ROI.clamped_to`, so the flip's frame-for-frame equivalence
holds by construction rather than by two implementations agreeing.
"""

from __future__ import annotations

import numpy as np

from sieve.backend.dispatch import Backend, kernel
from sieve.core.filter_base import (
    ArraySpec,
    CaptionPart,
    CostEstimate,
    ElementRelation,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import ROI, Frame, WorkUnits

#: Extent of the unbounded region, per axis. Any frame is smaller, so clamping
#: it yields that frame exactly. `1 << 20` rather than a machine maximum: it is
#: two orders of magnitude past 8K, which is enough to be unreachable and small
#: enough that a reader meeting `1048576` in a saved document can tell it is a
#: bound and not a measurement.
WHOLE_FRAME_EXTENT = 1 << 20

#: The identity crop. A value, not an absence — see the module docstring.
WHOLE_FRAME = ROI(x=0, y=0, width=WHOLE_FRAME_EXTENT, height=WHOLE_FRAME_EXTENT)


@register_filter(
    filter_id="crop",
    version="1.0.0",
    summary="Take a rectangular region of every frame.",
    # Unconstrained on both sides: a slice cares about neither dtype nor
    # channel layout, and declaring either would reject frames this handles.
    accepts=ArraySpec(),
    emits=ArraySpec(),
    # One output element is one input element — cropping decides *which* values
    # survive and never what one of them is a value of. A count over a crop of
    # `block_signal`'s output is still a count of blocks.
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        # A non-identity crop is one contiguous copy of the retained pixels.
        # The identity crop returns a contiguous view and pays effectively no
        # per-pixel work, but the static declaration has to hold for the copied
        # path.
        work_per_megapixel=WorkUnits(1.0),
        # Input plus an output no larger than it, no scratch.
        peak_bytes_per_input_byte=2.0,
    ),
    mode=Mode.STREAMING,
    primary_params=("roi",),
    caption=(CaptionPart(param="roi"),),
)
class CropParams(ParamsBase):
    """Which region of the input frame survives.

    `frame_bytes_ratio` is deliberately left at 1.0 rather than overridden. The
    fraction a crop keeps is `roi.area` over the input frame's area, and the
    second term is not a parameter — an unbounded region keeps all of it and a
    64x48 region keeps a different fraction of every resolution it meets. 1.0 is
    the bound, which is the safe direction for a prediction that decides whether
    a run is worth starting.
    """

    #: The region, in the coordinates of *this filter's input*. Defaults to the
    #: unbounded region, which clamps to whatever frame arrives — that is what
    #: "no crop" is spelled as, and it is why this field has no `None`.
    roi: ROI = WHOLE_FRAME


@kernel(CropParams, Backend.CPU)
def crop_cpu(frame: Frame, params: CropParams) -> Frame:
    """The region of `frame` this node declares, trimmed to what arrived.

    Copied rather than returned as a view, for `downsample`'s reason: a slice
    keeps the whole input frame alive, and a cached crop node holding one is the
    entire point of cropping defeated, one retained frame per stored entry.
    `executor._crop` returns the view because its result is consumed
    immediately; the pixels are identical either way.
    """
    region = params.roi.clamped_to(frame.width, frame.height)
    return Frame(
        data=np.ascontiguousarray(region.crop(frame.data)),
        index=frame.index,
        channels=frame.channels,
    )
