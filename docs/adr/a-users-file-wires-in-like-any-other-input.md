---
title: A user's file wires in like any other input
adr: 18
position: "04.04"
status: settled
decided: 2026-08-07
amended: 2026-08-07
---

A node's input may be wired to an upstream node or to a file the user picked.
Both wire the same way; only the key differs — derived from the graph, or from
the file's own content identity.

The case it is for: a user saves two background models, wires one into
background subtraction, then swaps it for the other to see which detects
better. That is a wire moving, and it should cost what any other edit costs.
Nothing in the tree lets a tool ask for that input today, which is the only
thing missing — the wiring underneath it is built. A written crop "is a child
source with its own identity, not the parent's" (`core/pipeline_model.py`) and
the executor serves it where it would otherwise have run `crop`; a checkpoint is
the same substitution in the other direction, and Phase 5's gate is that a rerun
reading written artifacts equals the run that computed them *with every cache
key unmoved* ([PLAN.md](../PLAN.md)). A file already stands where a node stood,
twice, each time for one hardcoded case.

One route, not two. A separate path through the executor for user-supplied
inputs is what [one-execution-path](one-execution-path.md) refuses on the
preview/production axis, for the reason that applies here unchanged: with two
routes, the one that was tuned against is not the one that runs.

What the key is derived *from* is the whole difference. An upstream input's key
is computed from the graph, so an edit propagates. A picked file has nothing
upstream to constrain it, so its key is the file's own content identity —
`source_key` and `decoder_identity()` exist for exactly that. Get this wrong and
the swap above is invisible to the store, which serves the first model's results
under the second's name: well-formed key, plausible frame, no symptom.

**Resolution policy stays out of the key.** What is hashed is the resolved
file's identity, never the rule that found it — neither "this exact path" nor
"the folder of this name beside the project". A rule in the key makes two
projects naming one file disagree about it; a rule *instead of* identity makes
one project agree with itself after the folder is reorganized underneath it.
`SourceRef` already separates the two for the project's own video, storing a
path relative to the project directory so the project moves while identity comes
from the file.

Two consequences rather than decisions. Which file a node reads changes its
output, so it is a param and is saved
([param-not-preference](param-not-preference.md)). And a path param is a
presentation stereotype whose handoff surface is a file or folder picker, which
is [gui-knows-kinds-not-tools](gui-knows-kinds-not-tools.md)'s licensed
extension: the tool declaring one writes no GUI code.

This says nothing about what travels along the wire. That is `StreamKind`'s
question — arrays and tables today, `detect` consuming a signal series rather
than frames — and it stays open on the usual terms
([a-tool-is-one-file](a-tool-is-one-file.md)). Nor does it settle what a frame
index means when two inputs are videos of different lengths, whether a graph may
have more than one root (`Project.source` is singular and `source_key` calls
itself the ancestor of every root), or how an input that is one value for the
whole run rather than one per frame is handed over.
