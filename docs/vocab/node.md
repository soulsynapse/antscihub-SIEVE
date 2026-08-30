---
title: node
group: Substrate
position: 7
gloss: Two live senses about the same running system that disagree about who counts — a role a tool fills because it offers an edge, and anything that declares a need on the store.
origin: emergent
status: unsettled
raised: 2026-08-30
---

Two live senses that are the same noun about the same running system and
disagree about who counts, plus an instance sense nothing defines and a
borrowed one that collides with nothing. The contract's node is a role a tool
fills, and you are one because you offer an [edge](edge.md). The orchestrator's
node is anything that declares a need on the store, and you are one because you
declared — which makes the GUI a node, and the GUI can never be the other kind.

## Senses

**A role a tool fills**, in `contract/nodes.py`: `Source` is "a node with no
inputs", `Step` is "a node with frame inputs", `ROLES` is the closed table of
them, and `contract/edges.py` opens with "what may travel between nodes". This
is the only word in the vocabulary with its definition enforced at run time —
`Step.__post_init__` raises "a step that offers nothing is not a node". Worth
noting where it does *not* appear: `fill.py`, `serve.py` and `store.py` all
import from `contract/nodes.py` and none of them calls anything it holds a
node. They say tool, source, output, step. The word lives entirely in the
contract that mints the roles.

**A consumer that declares a need**, in
`experiments/orchestrator-experiments/graph.py`: "the GUI, a tool, the series
writer, the proxy builder — each is a node that declares what form it wants,
which positions relative to its own it needs held, and a pressure."

**A slot in a chain with a durable id**, in `mockup/mockup.py`: `NODES` is
`(id, tool)` pairs, `retool` "puts another tool at index, keeping the node it
is", `add_node` mints one, and the ids are what the edges and the ticks hang
on.

**An AST or tree node**, in `checks/adr0010.py` and `scripts/doc_index.py` —
ordinary Python, the same harmless shape as [edge](edge.md)'s border sense.

## Fork

The first two are the problem, and the reason is that the second was reached by
widening the first on purpose rather than by anyone slipping. `graph.Need`
carries a form, offsets and an urgency, which is `Step`'s declaration
"generalised to every consumer" in that module's own words. Widened that far,
node stops meaning *a thing a tool can be* and starts meaning *a thing the
scheduler serves*, and then `contract/edges.py`'s opening line is false of most
nodes: nothing travels between the GUI and the proxy builder, and neither of
them offers a name anything could bind. The sense has already left the
experiment — `docs/findings/2026.08.30-the-pressure-dispatcher-preempts-into-seeks.md`
says a decode was "attributed to whichever node happened to be served next",
meaning a fill sweep, which is substrate and holds no role at all.

The third sense is not a competitor but a gap. The contract has no node
instance anywhere: no id, nothing that persists when the tool in a slot is
swapped, nothing a [binding](binding.md) could name twice in one chain. The
mockup needed exactly that on the first screen where a step could be retooled,
and invented it. Whatever happens to the first two, something has to be called
the thing that keeps its identity across a swap.

Which of the two graph senses keeps the word. The cheap direction is the
contract keeping it: `contract/nodes.py`, `ROLES` and the raise are
load-bearing, while the orchestrator's is one experiment plus one sentence in a
finding, and a rename there costs a field name and a docstring. The argument
against is that the orchestrator is what lands next: if everything the
scheduler serves is a node, the GUI *is* a participant and "a node offers an
edge" is the narrow reading that needs the edit, in `Source` and `Step`'s first
lines rather than in the experiment. ADR-0009 says in as many words that
"whether a tool is a node ... reopens on evidence" — this is the only
vocabulary entry whose own decision record states the question is open, and the
module defining toolhood is named for the answer. Nothing would go red either
way. Not decided: the file that lands the orchestrator in `src/` will both
import `contract/nodes.py` and hold a `Need`, and whoever writes it picks.
