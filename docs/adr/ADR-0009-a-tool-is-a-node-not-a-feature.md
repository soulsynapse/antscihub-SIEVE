---
title: A tool is a node, not a feature
group: Substrate
position: 9
status: settled
decided: 2026-08-24
---

An analysis is a node in a graph that SIEVE evaluates. SIEVE owns the frames,
the graph and the scheduling, and never owns the analyses. Adding a way to
measure something is adding a node, and it is never a change to SIEVE.

What this is for is a cap. Without the boundary, every new thing anybody wants
to measure is another feature inside SIEVE, and SIEVE is a program with no
state in which it is finished — each analysis arriving as one more extension of
the base functionality, growing a codebase whose scope is defined by whatever
has been asked for so far. With the boundary, SIEVE is a fixed thing: it gets
frames in a named form, correctly and fast; it plans and schedules a graph over
them; it shows what the graph produced; and it routes an interaction to a node
that asked for one. That list can be completed. The set of things an
ethologist might want to measure cannot, which is exactly why the two must not
be the same codebase.

This is not an argument about third-party authorship and does not depend on
one. The cap pays at one author, because what it buys is a definition of done.

## What the boundary costs, and what it is worth

Priced rather than asserted, in `experiments/chain-experiments/`. The figures
live in that folder's result files, where a later measurement supersedes an
earlier one by sitting beside it; what belongs here is which way each answer
came out.

**Generality is affordable, and it is priced in bytes rather than in calls.**
An edge costs the intermediate it names and not the call that names it — the
cost scales with the array, which is the opposite of how dispatch overhead
behaves. A graph deep enough to be worth calling a graph spends a small share
of a frame period on its joints. This was the answer that could have refused
the decision, and it did not.

**A graph still has a fetch plan.** This is the load-bearing one, because the
product constraint is not that graphs are fast but that they refill faster than
the video plays, and that is only reachable by prefetching. A plan for a graph
nobody has run is computable from declarations alone, which also means
scheduling and costing stay separable — a novel graph is prefetched correctly
on its first pass, before ADR-0007 has any measurement of it to offer.

**Depth is affordable to hold.** The point set at one position multiplies with
depth; the working set over a moving playhead grows only by the added reach. So
ADR-0006's distinction between what must be resident to evaluate a position and
what must be held to serve a run is what makes depth cheap, rather than a
refinement of it.

## What the decision requires

Three terms, and none is independently choosable. Each is what some already
settled decision costs once analyses are nodes rather than features, which is
why they are consequences here and not decisions of their own.

**A node declares its offsets against its own inputs, never against the
source.** A node reading another at four lags says four lags *of that node*,
and the source rows follow by composition down to the root. Declared against
the source instead, every node would have to know its whole upstream chain to
state its needs — an edit anywhere upstream would silently invalidate every
declaration below it, and the plan ADR-0006 requires could not be assembled
from parts. The composition is arithmetic and is checked in `02`.

**A node's key folds its entire upstream subgraph.** A key naming only local
parameters is correct for a flat bank of independent readers, because there is
no upstream; it is wrong the moment nodes feed each other, and wrong silently —
two graphs differing only in an upstream parameter are filed under one name and
the second reads the first's numbers. Nothing about cost changes when a value
is filed under the wrong name, which is why this is the term most likely to
survive into a release undetected, and why `05-provenance`'s invariant is the
one that catches it. The tree already does this at depth one: the explorer
chains a blur by folding its parameter into the downstream tool's key.

**A node producing a field and a node reducing it are scheduled together.**
They may be written as two nodes. They may not be evaluated as two, because a
field surviving between two schedulable units is a field in storage, and a
field is image-sized per row per parameter setting. Fusing them is what keeps
that refusal true.

## What this does not decide

Named so that none of them is settled by implication.

**Whether there is a published API and a closed set of base types.** The
measurements are about scheduling and say nothing about a type contract.
`01`'s re-expression of the working explorer found six types and could not
validate a mask, because nothing in the tree produces one — so a boundary
committed now would be committed on evidence that was never about it. The
internal graph does not need the question answered.

**Whether the user chooses what is kept.** Keeping an intermediate saves
compute in proportion to declared reuse and spends frame-cache room, and which
wins inverts with what the inputs cost to fetch — a node worth keeping when its
inputs come from a derived file is worth recomputing when they come from a
decode. So a policy is needed. Whether the policy is the substrate's or the
user's, and whether a person can tell what they are choosing, is not answered
by knowing that it inverts.

**Whether a graph is a line.** ADR-0003 swipes project → pipeline → step, and a
line has a next step where a graph does not. What the right pane's middle
position means once analyses are a DAG is open, and is a question about that
ADR rather than this one.

**Where a rate change would go.** The composition arithmetic assumes every node
shares the source's row space (ADR-0004). A node emitting one value per several
rows would have a row space of its own and the arithmetic would not be defined.
Nothing does this today; it is recorded because it is the one shape known to
fall outside the terms above rather than merely to be unbuilt.
