---
title: A user's file wires in like any other input
adr: 18
position: "04.04"
status: settled
decided: 2026-08-07
amended: 2026-08-07
---

Note: Even if this looks like a review wrote it, I wrote it.

A file a user picks enters as a **source tool** — a node with no upstream — so
every input is an edge. Only the key differs: a graph-fed node keys from the
graph, a source tool from its file.

The case it is for is VISION's picker and folder scenarios — a background made
outside the project standing where a generated one stood, and a folder of videos
read either as one concatenated source or as one source per replicate. Both are
a file where a node's frames come from, and neither is a new kind of edge.
Nothing in the tree lets a tool ask for that today, which is the only thing
missing — the wiring underneath it is built. A written crop "is a child source
with its own identity, not the parent's" (`core/pipeline_model.py`) and the
executor serves it where it would otherwise have run `crop`; a checkpoint is the
same substitution in the other direction, and Phase 5's gate is that a rerun
reading written artifacts equals the run that computed them *with every cache
key unmoved* ([PLAN.md](../PLAN.md)). A file already stands where a node stood,
twice, each time for one hardcoded case.

**A tool, not a param on the consumer.** Making the consuming node carry which
file it reads would give the document two ways to say where input comes from —
an edge when it is a node, a param when it is a file — and put one control in
front of the user emitting two different mutations. A source tool collapses
that: adding a file is adding a node, choosing among sources is moving an edge,
and the command layer needs no intent kind it does not already have. It is also
what [a-tool-is-one-file](a-tool-is-one-file.md) predicts — reading a new kind
of file is a tool, bought for one module.