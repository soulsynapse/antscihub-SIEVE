---
title: A user's file wires in like any other input
adr: 18
position: "04.04"
status: settled
decided: 2026-08-07
amended: 2026-08-07
---

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

One route, not two. A separate path through the executor for user-supplied
inputs is what [one-execution-path](one-execution-path.md) refuses on the
preview/production axis, for the reason that applies here unchanged: with two
routes, the one that was tuned against is not the one that runs.

What the key is derived *from* is the whole difference. A node fed by the graph
keys from the graph, so an edit propagates. A source tool has nothing upstream
to constrain it, so its key is the file's own content identity — `source_key`
and `decoder_identity()` exist for exactly that. Get this wrong and swapping one
background for another is invisible to the store, which serves the first
model's results under the second's name: well-formed key, plausible frame, no
symptom.

**Resolution policy stays out of the key.** What is hashed is the resolved
file's identity, never the rule that found it — neither "this exact path" nor
"the folder of this name beside the project". A rule in the key makes two
projects naming one file disagree about it; a rule *instead of* identity makes
one project agree with itself after the folder is reorganized underneath it.
`SourceRef` already separates the two for the project's own video, storing a
path relative to the project directory so the project moves while identity comes
from the file. A source tool's file param resolves per replicate through the
ordinary overrides path, so one node can name a pattern and each replicate
resolve its own file — which is what makes a folder of pre-cropped videos
expressible without a second mechanism — and what is hashed is still the file
each replicate resolved to. A pattern resolving to nothing is a run that cannot
happen; one resolving to several is refused rather than ordered, because "the
first match" is the filesystem's answer and not the project's.

Three consequences rather than decisions. Which file a node reads changes its
output, so it is a param and is saved
([param-not-preference](param-not-preference.md)). A path param is a
presentation stereotype whose handoff surface is a file or folder picker, which
is [gui-knows-kinds-not-tools](gui-knows-kinds-not-tools.md)'s licensed
extension: the tool declaring one writes no GUI code. And a source that is one
value for the whole run broadcasts it across the span, so a static input needs
no window shape the per-frame machinery does not already have.

**A source tool is a root by construction**, and the project's own video is not
its ancestor. Where a single root is assumed — the order a graph is drawn in,
the source key, and the executor's binding of a node with no upstream — is what
the first source tool moves. That migration is an item; the decision here is
only that the root is legal and keys from its own file.

This says nothing about what travels along the wire. That is `StreamKind`'s
question — arrays and tables today, `detect` consuming a signal series rather
than frames — and it stays open on the usual terms
([a-tool-is-one-file](a-tool-is-one-file.md)). Nor does it settle what a frame
index means when two inputs are videos of different lengths.
