"""Take a region of every frame, with the whole frame as the identity value.

v2's crop began life inside `pipeline/executor.py` as `_crop`, applied from a
region the plan carried beside the graph, where no cache key could see it and no
graph could place it. Making
it a step cost nothing structural — it was already frame-in, frame-out and
streaming — and bought the two things a special case cannot have: a position in
the graph and a contribution to the key. v3 has no other shape available to it
(`adr/no-kernel-apparatus.md`), so what carries over is the argument, not the
migration.

**The region is denominated in this node's *input* space, not in source
pixels.** `ROI` promises integer pixel coordinates and nothing about which array
they index; the field that holds one decides that, and here it is whatever frame
arrives. A crop placed after a `rescale` indexes the rescaled frame, and nothing
in this module could convert between the two. Whoever synthesizes a crop from a
replicate's region must therefore put it at the *root*, where this input space
and `CropRecord.region`'s source space coincide.
`test_crop.py::test_a_second_crop_is_denominated_in_the_first_s_output` is what
fails if anything starts assuming otherwise.

**"No crop" is `WHOLE_FRAME`, never `None`.** The identity of a present
parameter, so that no `X | None` propagates through the plan and every caller is
spared a branch that has exactly one correct arm. `ALL_FRAMES` in
`core/tool_base.py` is the same move on the time axis, and cites this one for
the reason below. The extent is unbounded
rather than the frame's own because a full-frame region in pixels cannot be
written by anything that has not opened the video, and the writers that need it
have not: a hand-typed YAML, and anything synthesizing a graph from a document
that records no source dimensions. An unbounded region clamps to exactly the
frame it meets, which makes "the whole of it" a value both of them can write.

The operation is therefore the *intersection* of the declared region with the
frame. Clamping is not leniency about a bad value: a reader can hand back a
smaller frame than the region was drawn against, and the same clamp is what
makes the identity value expressible at all.
"""

from __future__ import annotations

import numpy as np

from sieve.core.tool_base import (
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Mode,
    ParamsBase,
    ParamStereotype,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import ROI, Frame, FrameSpan

#: Extent of the unbounded region, per axis. Any frame is smaller, so clamping
#: it yields that frame exactly. `1 << 20` rather than a machine maximum: it is
#: two orders of magnitude past 8K, which is enough to be unreachable, and small
#: enough that a reader meeting `1048576` in a saved document can tell it is a
#: bound and not a measurement.
WHOLE_FRAME_EXTENT = 1 << 20

#: The identity crop. A value, not an absence — see the module docstring.
WHOLE_FRAME = ROI(x=0, y=0, width=WHOLE_FRAME_EXTENT, height=WHOLE_FRAME_EXTENT)


def run(params: CropParams, window: FrameSpan, state: None, /) -> Frame:
    """The region of the target frame this node declares, trimmed to what arrived.

    Copied rather than returned as a view, for `downsample`'s reason: a slice
    keeps the whole input frame alive, so a cached crop node would retain one
    decoded frame per stored entry — the point of cropping defeated, one
    retained frame at a time and visible only as memory.
    """
    frame = window.target
    region = params.region.clamped_to(frame.width, frame.height)
    return Frame(
        data=np.ascontiguousarray(region.crop(frame.data)),
        index=frame.index,
        channels=frame.channels,
    )


@register_tool(
    tool_id="crop",
    version="1.0.0",
    summary="Take a rectangular region of every frame.",
    # Unconstrained on both sides: a slice cares about neither dtype nor channel
    # layout, and declaring either would reject frames this handles.
    accepts=ArraySpec(),
    emits=ArraySpec(),
    run=run,
    # One output element is one input element — cropping decides *which* values
    # survive and never what one of them is a value of. A count over a crop of
    # `block_signal`'s output is still a count of blocks.
    element=ElementRelation.PRESERVED,
    mode=Mode.STREAMING,
    primary_params=("region",),
    caption=(CaptionPart(param="region"),),
    # The declaration Phase 7's canvas handoff reads. It says the value is a
    # rectangle in the frame this node is handed; which surface draws it, and
    # what that surface does about a node that is not at the root, are that
    # phase's questions and not answerable here.
    param_stereotypes={"region": ParamStereotype.REGION},
)
class CropParams(ParamsBase):
    """Which region of the input frame survives."""

    #: In the coordinates of *this node's input*. Defaults to the unbounded
    #: region, which clamps to whatever frame arrives — that is what "no crop"
    #: is spelled as, and it is why this field has no `None`.
    region: ROI = WHOLE_FRAME
