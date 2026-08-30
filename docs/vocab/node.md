---
title: node
group: Substrate
position: 7
gloss: Two live senses about the same running system that disagree about who counts — a role a tool fills because it offers an edge, and anything that declares a need on the store.
origin: emergent
status: unsettled
raised: 2026-08-30
---

Two senses that are the same noun about the same running system and disagree
about who counts, plus an instance sense nothing defines. The contract's node
is a role a tool fills, and you are one because you offer an [edge](edge.md).
The orchestrator's node is anything that declares a need on the store, and you
are one because you declared — which makes the GUI a node, and the GUI can
never be the other kind.

## Senses

**A role a tool fills**, in `contract/nodes.py`: `Source` is "a node with no
inputs", `Step` is "a node with frame inputs", `ROLES` is the closed table.
This is the only word here enforced at run time — `Step.__post_init__` raises
"a step that offers nothing is not a node". Where it does *not* appear is worth
as much: `fill.py`, `serve.py` and `store.py` import that module and call
nothing a node.

**A consumer that declares a need**, in
`experiments/orchestrator-experiments/graph.py`: "the GUI, a tool, the series
writer, the proxy builder — each is a node that declares what form it wants."

**A slot in a chain with a durable id**, in `mockup/mockup.py`, where `retool`
"puts another tool at index, keeping the node it is". **An AST node**, in
`checks/adr0010.py` — ordinary Python, no contest.

## Fork

The second sense was reached by widening the first on purpose. `graph.Need` is
`Step`'s declaration "generalised to every consumer", and widened that far,
node stops meaning *a thing a tool can be* and starts meaning *a thing the
scheduler serves* — at which point `contract/edges.py`'s "what may travel
between nodes" is false of most of them.

The cheap direction is the contract keeping it: `ROLES` and the raise are
load-bearing, and renaming in the experiment costs a field name and a
docstring. The argument against is that the orchestrator lands next, and if
everything the scheduler serves is a node then "a node offers an edge" is the
line that needs the edit. ADR-0009 already says "whether a tool is a node ...
reopens on evidence". Nothing goes red either way. The file that lands the
orchestrator in `src/` will import `contract/nodes.py` and hold a `Need`, and
whoever writes it picks.

The third sense is a gap, not a competitor: the contract has no node instance
anywhere — no id, nothing that survives swapping the tool in a slot, nothing a
[binding](binding.md) could name twice in one chain.
