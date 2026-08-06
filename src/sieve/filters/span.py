"""Keep a range of frames, with every frame there could be as the identity value.

REWORK.md R1 applied to the other thing that was deciding a result from outside
the graph. The span was `ClipRange` on the `Project`, handed to
`ExecutionPlan.build` as an argument and read by the executor's yield: which
frames were in the answer was a fact about the *call*, so two runs of one graph
over different spans were the same graph, and nothing a cache key could see said
otherwise. This module is the same selection declared as a filter, discovered
like every other, with its bounds hashed into what the result is.

**The kernel is the identity, and that is the whole design rather than a gap in
it.** A selection has two halves on opposite sides of rule 7's line. Which frames
are in the answer is what the result *is*, and it is declared here, in parameters
that reach the digest. Not decoding the ones that are not is where they live and
how fast they arrive, and it is `ExecutionPlan`'s: the plan folds this range into
`span` and the reader is asked for `decode_range` — the span widened by the
lead-in — so the frames this node would have dropped were never read. That is a
predicate pushdown, and the reason it is sound is that the two halves cannot
disagree: one range, declared once, applied once.

So the kernel is handed only frames the plan already selected, plus the lead-in
below `span.start`, and it passes both through. **It must not refuse the lead-in**
— those frames are what warms every stateful filter in the graph, they are cut at
the yield after they have done that warming, and a selection that dropped them at
a root would leave everything downstream unsettled for the whole span. There is
consequently nothing left for this kernel to check that the plan has not already
made true, and a check written anyway would fire only when the fold was wrong,
which is a test's job and not a per-frame branch's.

**Put it at a leaf.** Placement changes nothing about the result — a graph has
one frame set, so a selecting node narrows the whole run wherever it sits
(`plan._selected`) — which leaves the cache as the only thing that can tell the
two apart, and it prefers the leaf sharply. A span node's parameters are folded
into every downstream node's key, so a span at the root means dragging the clip
bounds recomputes the entire graph for frames whose pixels did not change. At a
leaf the only entries it invalidates are its own, and its own are the identity.
This is the mirror of `crop.py`'s "put it at the root", argued from the other
end: a crop must sit where its coordinate space is the source's, and a span must
sit where its bounds poison nothing.
"""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from sieve.backend.dispatch import Backend, kernel
from sieve.core.filter_base import (
    UNBOUNDED_FRAME,
    ArraySpec,
    AuthoringGroup,
    CaptionPart,
    CostEstimate,
    ElementRelation,
    Mode,
    ParamsBase,
)
from sieve.core.filter_registry import register_filter
from sieve.core.types import Frame, WorkUnits


@register_filter(
    filter_id="span",
    version="1.0.0",
    summary="Keep only the frames in a range.",
    # Unconstrained on both sides, for `crop`'s reason: selecting frames cares
    # about neither dtype nor channel layout, and declaring either would reject
    # frames this handles perfectly well.
    accepts=ArraySpec(),
    emits=ArraySpec(),
    # A frame that survives is the frame that arrived, unchanged in every way
    # including what one of its values is a value of.
    element=ElementRelation.PRESERVED,
    cost=CostEstimate(
        # Zero, and not a small measured number. The kernel is `return frame`:
        # there is no per-pixel work for a per-megapixel figure to be
        # proportional to, so any nonzero value here would be call overhead
        # wearing a resolution's units. What this node actually saves is the
        # decode of everything outside the range, and that saving is the
        # planner's — a cost model over nodes has nowhere to put it.
        work_per_megapixel=WorkUnits(0.0),
        # The output *is* the input. No copy, no scratch.
        peak_bytes_per_input_byte=1.0,
    ),
    authoring_group=AuthoringGroup.SOURCE_PREP,
    authoring_order=60,
    mode=Mode.STREAMING,
    selecting=True,
    primary_params=("start", "end"),
    caption=(
        CaptionPart(label="start", param="start"),
        CaptionPart(label="end", param="end"),
    ),
)
class SpanParams(ParamsBase):
    """Which frames survive, half-open, in source indices.

    Two ints rather than a range type: these are saved parameters, and a `range`
    has no pydantic form that reads as anything in YAML. `selected_frames` below
    is where the pair becomes the interval the plan folds, which is the one place
    the half-open convention is stated in code.
    """

    #: First frame kept.
    start: int = 0
    #: One past the last frame kept. Defaults to `UNBOUNDED_FRAME` — past any
    #: footage, so the default range meets every video as the whole of it. That
    #: is what "no span" is: a value of this parameter rather than the absence of
    #: the node, for the same reason `crop.WHOLE_FRAME` is, and the same writers
    #: force it — a document is written by things that have not opened the video
    #: and cannot know its length.
    end: int = UNBOUNDED_FRAME

    @model_validator(mode="after")
    def _ordered_and_nonempty(self) -> Self:
        """`ClipRange`'s check, at the node that replaces it.

        A backwards or empty range is refused here rather than folded into an
        empty intersection in `plan._selected`, because the two are different
        mistakes: an empty *intersection* is two ranges that each make sense and
        do not overlap, and the reader has to be told which pair. An empty range
        on one node makes no sense on its own and the node is the whole message.
        """
        if self.start < 0:
            raise ValueError(f"span start must be non-negative, got {self.start}")
        if self.end <= self.start:
            raise ValueError(f"span must keep at least one frame, got [{self.start}, {self.end})")
        return self

    def selected_frames(self) -> range:
        """The declared range. Overriding it is what `selecting=True` promises."""
        return range(self.start, self.end)


@kernel(SpanParams, Backend.CPU)
def span_cpu(frame: Frame, params: SpanParams) -> Frame:
    """`frame`, unchanged.

    See the module docstring for why there is nothing here: the selection is
    applied by `ExecutionPlan.span`, and the frames that reach this kernel below
    `span.start` are the lead-in, which must pass through to warm what is
    downstream of it.
    """
    del params
    return frame
