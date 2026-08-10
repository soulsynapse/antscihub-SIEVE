---
title: A fan-in has no picture, and no rule for which parent a child hangs under
status: deferred
deferred_for: subject
gated_on: the-window-grows-a-port-keyed-form-and-the-executor-delays-each-port.md — until a document can hold two edges into one node there is no fan-in to draw or walk
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
