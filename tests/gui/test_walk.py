"""The three documents `walk.py` exists for, and none of which a chain shows.

`node_order` is written instead of `pipeline/dag.py`'s `linear_order` precisely
because a window must draw a document that branches, that is disconnected, and
that will not run. A three-node chain — the skeleton's fixture, and until now the
only document any case handed it — is the one shape whose walk order *is* its
document order, so every claim the module makes is invisible against it: roots
first, depth before breadth, and a node no root reaches emitted rather than
dropped all read the same as `tuple(pipeline.nodes)`.

Each case below is one of those three documents, and the document order is
chosen to disagree with the walk. A fixture whose two orders agree is not a
weaker version of these — it is green under a walk that does nothing.

No Qt here: `node_order` takes a `Pipeline` and returns nodes, so this file is
the one in this directory with nothing to defer.
"""

from __future__ import annotations

from sieve.core.pipeline_model import Edge, Node, Pipeline
from sieve.gui.walk import node_order


def graph(nodes: str, edges: str) -> Pipeline:
    """A pipeline from two spellings: node ids in document order, then edges.

    `"a b c"` and `"a>b b>c"`. The tool a node names is never read by a walk, so
    every node here is a `downsample` and the id carries the whole meaning.
    """
    return Pipeline(
        nodes=tuple(
            Node(node_id=node_id, tool_id="downsample", version="1.0.0")
            for node_id in nodes.split()
        ),
        edges=tuple(
            Edge(upstream=pair.split(">")[0], downstream=pair.split(">")[1])
            for pair in edges.split()
        ),
    )


def walked(pipeline: Pipeline) -> list[str]:
    return [node.node_id for node in node_order(pipeline)]


def test_a_branch_is_walked_depth_first_and_not_in_document_order() -> None:
    """`root` feeds `left` and `right`; `left` feeds `deep`.

    Saved `root left right deep`, because a document's order is whatever the
    edits that built it left behind and a user who added the second branch before
    descending the first gets exactly this. The walk still puts `deep` under
    `left`, which is the claim: a node is followed by what it feeds, not by
    whatever was written next.
    """
    order = walked(graph("root left right deep", "root>left left>deep root>right"))

    assert order == ["root", "left", "deep", "right"]


def test_a_root_is_reached_before_a_node_the_document_lists_earlier() -> None:
    """Two roots, and one of them is saved after the node it feeds.

    `fed` has a producer, so it may not open the walk however early the document
    puts it — the user's first Down would otherwise land in the middle of a chain
    with the step above it still unvisited. The two roots keep their own document
    order between themselves.
    """
    order = walked(graph("fed second first", "first>fed"))

    assert order == ["second", "first", "fed"]


def test_a_cycle_no_root_reaches_is_emitted_last_rather_than_dropped() -> None:
    """A runnable chain beside a two-node cycle `dag.py` will refuse.

    `Pipeline` admits this document and the window has to draw it: the cycle is
    what the user must reach to break, and a walk that dropped it would leave the
    only unrunnable part of the graph the one part unnavigable.
    """
    order = walked(graph("root tail loop back", "root>tail loop>back back>loop"))

    assert order == ["root", "tail", "loop", "back"]
