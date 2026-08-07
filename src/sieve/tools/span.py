"""Keep a range of frames, with every frame there could be as the identity value.

v2 carried the same argument `crop.py` records, on the time axis: which frames
were in the answer arrived beside the graph as a range on the project, handed to
the plan builder as an argument, so two runs of one graph over different spans
were the same graph and no cache key could say otherwise. Here
the selection is a tool, discovered like every other, with its bounds in the
params model that reaches the digest.

**The kernel is the identity, and that is the design rather than a gap in it.**
A selection has two halves. Which frames are in the answer is what the result
*is*, and it is declared in these parameters. Not decoding the ones that are not
is where they live and how fast they arrive, and it is `ExecutionPlan`'s: the
plan folds this range into `span` (`plan._selected`) and asks the reader for
`decode_range` — the span widened by the window — so the frames this node would
have dropped were never read. The two halves cannot disagree, because there is
one range, declared once and applied once.

So the kernel is handed only frames the plan already selected, plus the lead-in
below `start`, and it passes both through. **It must not refuse the lead-in** —
those frames are what warms every stateful tool in the graph, they are cut at
the yield after they have done that warming, and a selection that dropped them
at a root would leave everything downstream unsettled for the whole span. There
is consequently nothing left for this kernel to check that the plan has not
already made true, and a check written anyway would fire only when the fold was
wrong, which is a test's job and not a per-frame branch's.

**Put it at a leaf.** Placement changes nothing about the result — a graph has
one frame set, so a selecting node narrows the whole run wherever it sits — which
leaves the cache as the only thing that can tell the two apart, and it prefers
the leaf sharply. A span node's parameters are folded into every downstream
node's key, so a span at the root means dragging its bounds recomputes the entire
graph for frames whose pixels did not change. At a leaf the only entries
it invalidates are its own, and its own are the identity. This is the mirror of
`crop.py`'s "put it at the root", argued from the other end: a crop must sit
where its coordinate space is the source's, and a span must sit where its bounds
poison nothing.
"""

from __future__ import annotations

from typing import Self

from pydantic import model_validator

from sieve.core.tool_base import (
    UNBOUNDED_FRAME,
    ArraySpec,
    CaptionPart,
    ElementRelation,
    Emission,
    Mode,
    ParamsBase,
    ParamStereotype,
)
from sieve.core.tool_registry import register_tool
from sieve.core.types import Frame, FrameSpan


def run(params: SpanParams, window: FrameSpan, state: None, /) -> Frame:
    """The frame, unchanged and uncopied.

    Returned rather than rebuilt, which is the one place this tool differs from
    every other kernel in the package: `crop` and `downsample` copy because a
    view would retain the frame it was cut from, and here the output *is* that
    frame, so there is nothing a copy could release.

    See the module docstring for why there is no selection here: it is applied
    by `ExecutionPlan.span`, and the frames reaching this kernel below
    `params.start` are the lead-in, which must pass through to warm what is
    downstream of it.
    """
    del params, state
    return window.target


@register_tool(
    tool_id="span",
    version="1.0.0",
    summary="Keep only the frames in a range.",
    # Unconstrained on both sides, for `crop`'s reason: selecting frames cares
    # about neither dtype nor channel layout, and declaring either would reject
    # frames this handles perfectly well.
    accepts=ArraySpec(),
    emits=ArraySpec(),
    emissions=(Emission("selected"),),
    run=run,
    # A frame that survives is the frame that arrived, unchanged in every way
    # including what one of its values is a value of.
    element=ElementRelation.PRESERVED,
    mode=Mode.STREAMING,
    selecting=True,
    primary_params=("start", "end"),
    caption=(
        CaptionPart(label="start", param="start"),
        CaptionPart(label="end", param="end"),
    ),
    # Both bounds carry one stereotype because they are one populated value: the
    # generator that meets `span` reaches for a pair of timeline handles, and a
    # bound declaring `scalar-range` on its own would get a spinbox and take the
    # interval apart.
    param_stereotypes={
        "start": ParamStereotype.SPAN,
        "end": ParamStereotype.SPAN,
    },
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
        """The refusal at the node, rather than in the plan's intersection.

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
        """The declared range. Overriding it is what `selecting=True` promises.

        The default configuration returns a range *equal* to `ALL_FRAMES` rather
        than `ALL_FRAMES` itself, and that is enough: `plan._selected` compares
        by value, and two `range`s are equal when they are the same sequence. A
        branch returning the allocated constant would buy an `is` nothing asks
        for.
        """
        return range(self.start, self.end)
