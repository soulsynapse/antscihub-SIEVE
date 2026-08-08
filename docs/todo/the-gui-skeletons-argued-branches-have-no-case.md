---
title: The GUI skeleton's argued branches have no case
priority: normal
phase: 7
status: open
gated_on: nothing
done_when: "uv run python scripts/mutation_sweep.py --file src/sieve/gui/walk.py --mutant \"if node.node_id not in fed:==>if True:\" --mutant \"for child in children[node.node_id]:==>for child in ():\" --mutant \"return tuple(ordered)==>return tuple(pipeline.nodes)\" -- uv run pytest -q tests/gui"
opened: 2026-08-08
---

# The GUI skeleton's argued branches have no case

07.4 landed eight modules under one test. That is the shape the item asked for
— a skeleton is one capability — but three places in it argue a behaviour at
length and are held by nothing, and one of them is the reason a module exists.

`gui/walk.py` is written instead of `pipeline/dag.py`'s `linear_order`
precisely because a window must draw a document that branches, that is
disconnected, or that will not run. The only fixture is a three-node chain
whose document order *is* its walk order, so every one of those cases is
absent. Under `tests/gui`, all three of the mutants in `done_when` survive:
the roots-first pass, the recursive descent, and the accumulated order itself
— replacing the whole return with `tuple(pipeline.nodes)` is green. The branch
a module is written *for* has to be among the fixtures or the module is
unfalsifiable
(`findings/loop/2026.08.08-a-per-subject-revert-is-green-when-the-two-expressions-agree-on-every-fixture.md`,
2026-08-08 amendment). A branching graph, a two-root graph, and a cycle are
the three fixtures; schema v1 refuses two edges into one node, so a branch is
one node feeding two and a cycle is what `Pipeline` permits and `dag.py`
refuses at execution.

Two more, on the same sweep and not covered by the criterion above.
`layout._require_layout_section` raises on a Fixed or Maximum horizontal
policy and on a minimum wider than half the window; both branches survive
deletion, and no production caller can reach either — the canvas takes a
`QLabel` and the control side declares `Expanding`. It is the guard shape
already recorded for `_value_components`
(`the-arity-guard-accepts-a-union-nothing-asked-it-about.md`): the refusal
cases have to be written against widgets the tree does not otherwise hold.
And `control.show_graph` carries the rail's visibility across a rebuild rather
than deciding it, so that a walk moved from the project position does not put
a rail on a screen with no graph on it; `setVisible(True)` in its place
survives, because nothing moves the walk while the project position is
current.
