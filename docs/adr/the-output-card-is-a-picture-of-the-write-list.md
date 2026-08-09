---
title: The output card is a picture of the write list, not a node
adr: 25
position: "05.04"
status: settled
decided: 2026-08-09
---

The output step at the foot of the chain is drawn, not modeled: the GUI
renders a card over `Project.outputs` with edges derived from the ticks —
no output node, no sink shape in the tool contract.

The document never holds an output step and Run sits on the drawn card's
form; writing stays the run's act, as it already is.

Why: Phase 2 put `checkpoints` and `outputs` on `Project` for one
load-bearing reason — none of it may reach a cache key, so toggling what is
persisted cannot change what is computed (`PLAN.md` Phase 2). An output
*node* whose inputs are the ticked products would make every tick a graph
mutation, and the choice would be moving keys or a permanent exception in
the key walk. Drawing the card instead dissolves the contract question 09.2
was deferred on rather than answering it: edges-from-ticks is view state,
which the GUI legitimately owns (`gui-knows-kinds-not-tools.md`), and
`gui-computes-nothing` is untouched because deriving where a line lands is
not computing a result. The referent says "the output is a tool like any
other" (`mockup/mockup.py`, `WRITES`); ADR 22 reads the mockup for shape,
and this ADR keeps the shape — card, ticks-as-edges, Run at the foot — while
refusing the mechanism the referent's sample document could afford and the
schema cannot. The tree's only writer already behaves this way:
`storage/checkpoint_writer.py` writes as the run's act, not a shelf
declaration, and `tools/checkpoint.py` is only the read side
(`a-users-file-wires-in-like-any-other-input.md`) — so admitting a sink node
would have given the contract a shape its one existing writer never needed.
A consequence worth stating: the fan-in this step was expected to spend
(ports on `Edge`, the five one-input sites, the merge-key subject) does not
arrive here — it waits for a genuinely multi-input tool. Ruled 2026-08-09 at
`todo/the-output-is-a-step-and-its-ticks-are-edges.md`, which this unblocks.
