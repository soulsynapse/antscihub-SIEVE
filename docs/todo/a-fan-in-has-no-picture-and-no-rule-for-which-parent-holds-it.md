---
title: A fan-in has no picture, and no rule for which parent a child hangs under
status: open
gated_on: nothing
priority: normal
phase: "11"
done_when: "uv run pytest tests/gui/test_chain_edges.py tests/gui/test_walk.py -q -k 'a_second_parent_arrives_at_its_own_arrowhead or a_child_hangs_under_its_first_parent'"
opened: 2026-08-10
---

# A fan-in has no picture, and no rule for which parent holds it

11.2 makes a fan-in expressible and 11.3 lands the tool that needs one. Neither
draws it, and 11.3 may not — it is one file in `sieve.tools` with zero edits
elsewhere. What is left over is the surface: the stack draws one card per
position with the edges as geometry read off the cards at paint time
(`gui/chain_stack.py`), and every one of them comes from directly above.

**`walk.py` has already declared what it will do and can be asked nothing.** Its
docstring says every graph schema v1 admits is a forest because `Pipeline`
refuses two edges into one node, and that "the day a merging tool gives a node
two inputs this is the module that has to pick which parent a child hangs under
— with no edit anywhere below it." Both halves are subjectless: no test can build
the graph, and the sentence about the forest becomes false the moment 11.2 lands.
`node_order` visits a child from whichever parent it reaches first and marks it
seen, so it will not crash — it will silently hang the subtraction under
whichever of the two the document happens to list first, which is a choice made
by tie-breaking rather than by a rule anybody wrote.

The label is the same condition read from the other side. The referent names a
port only where a step has more than one input, "everywhere else the port is the
step above and a label would be a label saying 'the step above'" — so
`PORT_NAMES` and `_port_name` are drawn for exactly the case this item is about,
and the arrowhead is where the port a user picked
([which-axis-carries-a-meaning-like-generated-background.md](which-axis-carries-a-meaning-like-generated-background.md))
becomes visible.

The read-past is not part of this. `Pipeline.without_node` already fans a
removed node's inputs out to every reader — "both of them on the day a merging
tool gives a node two" — and the referent's `_sources_of` draws the same, so
dropping a subtraction hands both its ports down rather than cutting the chain
in two.

One thing to settle while here rather than after: `dag.linear_order` refuses a
branch because "a caller that draws a chain — the tool stack — can only host one
path", and the stack does not call it. It walks with `gui/walk.node_order`, and
`linear_order` is reached today only from `tests/unit/test_dag.py`. Whoever draws
the fan-in is the session that knows whether the refusal has a caller left.

`done_when` at minting, red because nothing matches — and red for as long as the
gate holds, since the two claims are about a graph no `Pipeline` accepts:

    $ uv run pytest tests/gui/test_chain_edges.py tests/gui/test_walk.py -q -k 'a_second_parent_arrives_at_its_own_arrowhead or a_child_hangs_under_its_first_parent'
    7 deselected in 0.14s
    exit: 5

## Folded 2026-08-10: the label is built, and three sites besides `walk.py` tie-break

Two corrections to the body above, both in this item's favour.

**The named arrowhead exists in `src/`, not only in the referent.** 09.2 built it
for the output card, which is the tree's one node with more than one input:
`ChainColumn.port_labels` derives the names, `port_label_origin` places one
beside its head, `_lifts` ranks a card's names so two of them are set as two
lines rather than through each other, `label_rect` is the geometric referent the
disjointness case reads, and `_paint_edge` writes them. So this item does not
invent the picture — it becomes the second caller of one that works, and what it
adds is the port name rather than the product name (the output card's edges are
named by what the *upstream* card emits, which is the one case where the reader
has nothing of its own to say).

That inheritance carries a defect 09.2's closing review recorded as unreachable
and named this caller for: `_lifts` ranks across every label on the column and
`label_headroom` is the max over all of them, while `PipelinePane` reserves that
spacing above the output card alone (`chain_stack.py`, the `addSpacing` before
`output_card`). A named edge into a *mid-stack* card therefore stacks by a global
rank and opens the gap in the wrong place — the names rise into the card above
and are painted under it, which the same review establishes is the same as not
being drawn. It is arithmetic today only because every label is an edge into the
foot.

**`walk.py`'s "with no edit anywhere below it" is false.** Three other sites read
the same refusal and each tie-breaks on its own:
`app.frame_bearing` and `pinned.element_kinds` both build
`{edge.downstream: edge.upstream for edge in pipeline.edges}`, which keeps the
**last** edge of a fan-in, and `MainWindow._feeding` — what the offer under a position
is computed from — takes the **first** through `next(...)`. Each carries a
comment citing the refusal by name, so none is an oversight; but the two
directions disagree, which means a fan-in landing without this item is not one
arbitrary choice made in one place, it is the canvas blending over one parent
while the offer is computed from the other. `the-canvas-shows-the-result-over-the-input.md`
(10.1) rests a paragraph on the same sentence and will ship before 11.2, so its
climb is the fourth site rather than a fifth question.

The rule the four then share is one ruling, not four: which parent a child hangs
under in the walk is what the canvas blends over and what the offer is computed
from, or the stack draws a chain the rest of the window is not talking about.

## Reviewed 2026-08-10: the gate lifted at `a318b55`, and the four sites now disagree in writing

`Pipeline` refuses two edges into one *port* and no longer two into one node, so
the graph this item is about is buildable — with a two-port spec declared
against a test's own registry, which is what `tests/unit/test_executor.py` now
does. No shipped merge tool is needed and none exists; 11.3 is not this item's
gate.

11.2 also did half of what this item's first paragraph asked for, in the
direction that makes the rest cheaper: every one of the four sites had a
docstring claiming there was never a parent to choose between, and each now
states its own tie-break instead — `gui/walk.py` first-reached,
`gui/app.py:frame_bearing` last, `gui/app.py:input_of` first,
`gui/pinned.py` and `gui/streams.py` last. So the disagreement is on the tree in
its own words and this item is the ruling over it rather than the discovery of
it. Nothing was *decided*, which is right: the docstrings all cite this file.

`gated_on` and `status` moved on the gate lifting. Nothing in the body below is
retracted.
