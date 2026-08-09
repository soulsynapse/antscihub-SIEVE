---
title: The output is a step, and its ticks are edges
step: "09.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests -q -k ticks_are_edges"
opened: 2026-08-09
---

# The output is a step, and its ticks are edges

What leaves the chain is a card at the foot of it, not a screen beside it:
the write list is the output step's param, ticking a product makes the step
that emits it an input of the output node — derived, so the picture cannot
disagree with the writes — the edges into the card are labeled by product,
and Run sits on the output's form. The save screen dissolves into it; its
pane was one step's form, so it is that step's form. MOCKUP-MAP.md row
"Output is a step" — `WRITES`, `refresh_output_inputs`, `_write_list`,
`_port_name`'s output branch and `_run_row` in the referent; VISION's
`output-1` guidance paragraph carries the argument. The map's review also
bounds it: the `into` folder and format combo on the referent's form are
*not* settled — the settled part is the shape. This spans layers by design —
an output tool on the shelf, the tick-to-edge derivation beside the graph,
the GUI rendering both — and the ticked list is what 07.9's checkoff becomes,
entering as the output node's param through the ordinary command path.

One edge per ticked product means this is the step where a node first has more
than one input, so it is the step that spends the extension ADR-2 anticipated:
`window` grows the port-keyed form [VISION.md](../VISION.md)'s scene calls for,
in the contract and the executor, not improvised tool-side by whatever tool
happens to be first to want two upstreams. That is also the event that gives
[a-merge-keys-its-inputs-by-port.md](a-merge-keys-its-inputs-by-port.md) the
subject it is deferred for — `a - b` versus `b - a` becomes crossable the
moment two labeled edges land on one node — so the run that builds this should
expect that item to come off its gate behind it, and should not reach the same
shape by a private route that leaves the deferral standing.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k ticks_are_edges
    1000 deselected in 0.93s
    exit: 5

## 2026-08-09 (review): the one-input posture is hardened at five sites, not one

Folded in rather than minted, because it is the same work this item already
owns. "The contract and the executor" is where the port-keyed form goes, but
the shape it replaces is not a default that a wider one quietly supersedes —
it is a refusal, installed deliberately and in five places.
`Pipeline._check` raises `two edges feed {node}` before any of the rest sees a
graph (`core/pipeline_model.py`); `Dag.node_keys`, `Dag._elements` and
`Dag._element_names` each unpack `(parent,) = fed` (`pipeline/dag.py`), and
`executor.py` does the same. `dag.py`'s own header cites the `Pipeline`
refusal as the reason it may assume one, and the last three of those unpacks
were *put there* by
[a-nodes-inputs-are-labeled-and-variadic.md](a-nodes-inputs-are-labeled-and-variadic.md),
now `done`, on the argument that silently keying on the first of two is the
failure being prevented. So the first ticked second product is a raise at
graph-construction time, well before anything can draw it, and unwinding the
five is inside this step rather than discovered by it. What replaces each is
the port-keyed read, not a drop of the check: the invariant that survives is
that an unlabeled second edge is still refused.

## 2026-08-09 (work): the output node is a shape the contract has no word for

Read before picking this up again: the run that measured this did not build,
and what stopped it is not size.

Every other clause here has a home in the tree already. `Edge` grows a port and
`Pipeline` keys its refusal on `(downstream, port)`; the five one-input sites
unwind against that; `window` grows the port-keyed form, which
[adr/no-kernel-apparatus.md](../adr/no-kernel-apparatus.md) names in advance as
"a contract-plus-executor change" and therefore licenses. The output *node* is
the clause with nothing behind it. It consumes one stream per ticked product
and emits none, and `ToolSpec` has no way to say that: `emits` is required and
typed, `_edge_faults` reads it, `Dag.elements` folds it, `ArraySpec.matches`
offers on it, and `executor._unrunnable_reason` refuses a spec that emits rows
because "a run returns a frame". A node that returns nothing is a member of the
declarable shape space that no ADR admits and this item does not rule on —
`adr/declared-means-verified.md` and the repo's ADR succession both put that
ruling ahead of the commit that spends it, not inside it.

The item is also not separable ahead of that ruling, which is worth stating
because the obvious split is the one that is closed.
[a-nodes-inputs-are-labeled-and-variadic.md](a-nodes-inputs-are-labeled-and-variadic.md)
argues that the schema may not grow a port field before a tool has ports — "the
distinction-nothing-can-make that `Edge` refuses" — so ports cannot land first.
And the five folds cannot unwind first either: what `_elements` reads once a
node has two upstreams is the merge semantics
[a-merge-keys-its-inputs-by-port.md](a-merge-keys-its-inputs-by-port.md) is
deferred on, and the only thing that dissolves the question is a node with no
element meaning to fold — the sink again. Every route in runs through the one
declaration nobody has made.

So the order is: rule on the sink shape, then this item builds in one piece —
ports, the five sites, the tool, the tick-to-edge derivation — with the GUI half
(the card at the foot of the stack, Run on its form, `gui/save_screen.py`
dissolving into it) a second job behind it. `done_when` is untouched and still
covers the whole; nothing here narrows it.