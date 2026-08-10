"""The order Up and Down move through a graph.

A linearization is a presentation choice, not a property of the document
(`adr/superseded/gui-base-is-the-v25-spike.md`): a graph that branches has many depth-first
walks and the pipeline layer has no reason to prefer one. So this lives here,
above the fence, and the layer below is asked nothing.

Not `pipeline/dag.py`'s `linear_order`, which is the neighbouring answer for a
neighbouring question: it refuses anything but a single chain, because its
caller draws seams and would otherwise draw ones that lie. This one never
refuses. A window has to render whatever document was opened — including a
branching one, a disconnected one, and one whose graph will not run — and a
walk that raised would take the whole skeleton down with it rather than the
part that cannot be drawn.

**A fan-in is expressible now, and this module has not chosen a rule for one.**
`Pipeline` refuses two edges into one *port* and no longer two into one node, so
a node may have two producers and the spanning tree is no longer the graph.
`node_order` visits a child from whichever parent reaches it first and marks it
seen, which is a choice made by the tie-break below rather than by anything
anybody decided — and three other sites tie-break the same question in their own
directions. Picking one rule for all four is
`todo/a-fan-in-has-no-picture-and-no-rule-for-which-parent-holds-it.md`, and it
is a choice made here with no edit anywhere below.
"""

from __future__ import annotations

from sieve.core.pipeline_model import Node, Pipeline


def node_order(pipeline: Pipeline) -> tuple[Node, ...]:
    """Every node exactly once, roots first, each followed by what it feeds.

    Ties — sibling branches, and the roots themselves — break on the document's
    own order, so the walk is stable across a save and reopen and a user's
    fifth Down lands where their fifth Down landed yesterday.

    A node no root reaches is emitted last rather than dropped. The only way to
    have one is a cycle, which `Pipeline` permits and `dag.py` refuses at
    execution; a step the user cannot navigate to would leave them unable to
    reach the node they must edit to make the document runnable again.
    """
    children: dict[str, list[str]] = {node.node_id: [] for node in pipeline.nodes}
    fed: set[str] = set()
    for edge in pipeline.edges:
        children[edge.upstream].append(edge.downstream)
        fed.add(edge.downstream)

    ordered: list[Node] = []
    seen: set[str] = set()

    def visit(node: Node) -> None:
        if node.node_id in seen:
            return
        seen.add(node.node_id)
        ordered.append(node)
        for child in children[node.node_id]:
            visit(pipeline.node(child))

    for node in pipeline.nodes:
        if node.node_id not in fed:
            visit(node)
    for node in pipeline.nodes:
        visit(node)
    return tuple(ordered)
