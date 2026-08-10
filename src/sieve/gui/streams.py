"""What each position of a document actually produces, folded from the source.

The offer under a step is computed from the stream flowing into it, and until
this walk existed it was handed the upstream node's declared `emits` — which is
not what a position produces. A preserving tool states neither dtype nor channel
layout because it emits what it was handed, so `crop` proved nothing and the box
under it was empty, and crop is the first tool in every pipeline
(`findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md`).

`pinned.element_kinds` is the same walk over the other half of the spec, and the
one thing not copied from it is its hardcoded `PIXEL` root: what a chain starts
from is the source *as the document names it*, so the seed is the root node's own
`emits`. Deriving it from the graph instead — `dag.graph_needs_chroma` is the
call that looks like the seed — would make the resolution unable to move when a
second file appears in the folder, which is the event VISION's new-project
scenario uses to define the feature.

No Qt here, and that is load-bearing rather than incidental: this is a fact about
the document, not a widget, and the unit test that measures the offer over the
real shelf should not have to build an application to ask.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sieve.core.pipeline_model import Node, Pipeline
from sieve.core.tool_base import StreamSpec, ToolSpec, node_stream


def stream_specs(
    order: Sequence[Node], pipeline: Pipeline, specs: Mapping[str, ToolSpec]
) -> dict[str, StreamSpec | None]:
    """The stream each step produces, resolved against the one flowing into it.

    `None` only where the step's own tool is missing, which is
    `resolved_specs`' leniency carried through rather than a second policy. It
    does not propagate the way `element_kinds`' `None` does, and the asymmetry
    is the declarations': a tool that states both fields of `emits` produces
    that stream whatever reached it, while `PRESERVED` says nothing at all
    without an upstream to name. A step below a missing tool therefore resolves
    exactly as far as its own declaration reaches, and no further.

    A fan-in keeps its *last* parent here, which is a tie-break and not a rule —
    one of the four that
    `todo/a-fan-in-has-no-picture-and-no-rule-for-which-parent-holds-it.md`
    settles together. `order` is the walk's, which is topological, so a step's
    input is resolved by the time it is reached.
    """
    upstream_of = {edge.downstream: edge.upstream for edge in pipeline.edges}
    resolved: dict[str, StreamSpec | None] = {}
    for node in order:
        parent = upstream_of.get(node.node_id)
        arriving = None if parent is None else resolved.get(parent)
        spec = specs.get(node.node_id)
        resolved[node.node_id] = None if spec is None else node_stream(spec.emits, arriving)
    return resolved
