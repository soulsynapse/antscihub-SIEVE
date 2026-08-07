---
title: An input is a keyed frame provider
adr: 18
position: "04.04"
status: settled
decided: 2026-08-07
---

A node's input is a keyed frame provider; whether it names an upstream node or
a file the user chose changes only how its key is derived, never what the
executor does with it.

Half of that pair is already built and named. `executor.FrameSource` is a
protocol with one method — `read(index) -> Frame` — and its docstring says
`VideoReader` satisfies it, so does a reader over a materialized crop, and so
does a list of frames in a test. The other half is the identity that keys it,
which `cache_key.source_key` produces for the graph's one root. This ADR says
an input is that pair, and that a run may hold several rather than one.

Why: v3 has built the substitution twice already, each time for a single case.
A written crop "is a child source with its own identity, not the parent's"
(`core/pipeline_model.py`), and the executor serves it where it would otherwise
have run `crop`. A checkpoint is the same move in the other direction, and
Phase 5's gate is that a rerun reading written artifacts equals the run that
computed them *with every cache key unmoved* ([PLAN.md](../PLAN.md)). Frames
from a node and frames from a file are already interchangeable below the key;
what is missing is that a tool cannot ask for the second kind. The alternative —
a second input concept with its own route through the executor — is what
[one-execution-path](one-execution-path.md) refuses on the preview/production
axis, and for the same reason: with two paths, the one that was tuned against
is not the one that runs.

Derivation is where the two differ, and it is the whole of the difference. An
upstream input's key is computed from the graph, so an edit propagates. A
user-designated file has nothing upstream to constrain it, so its key comes from
the file's own content identity — `source_key` and `decoder_identity()` exist
for exactly that. The failure this prevents is not hypothetical: saving two
background models and swapping them to see which detects better is an ordinary
tuning action, and a swap the key cannot see serves the first model's frames
under the second's name. Well-formed key, plausible frame, no symptom.

**Resolution policy stays out of the key.** What is hashed is the resolved
file's identity, never the rule that found it — neither "this exact path" nor
"the folder of this name beside the project". A rule in the key makes two
projects naming one file disagree about it; a rule *instead of* identity makes
one project agree with itself after the folder is reorganized underneath it.
`SourceRef` already separates the two for the project's own video, storing a
path relative to the project directory so the project moves while identity
comes from the file.

Two consequences fall out rather than being decided here. Which file a node
reads changes its output, so it is a param and is saved
([param-not-preference](param-not-preference.md)). And a path param is a
presentation stereotype whose handoff surface is a file or folder picker, which
is [gui-knows-kinds-not-tools](gui-knows-kinds-not-tools.md)'s licensed
extension: the tool declaring one writes no GUI code.

What this does not settle, and does not pretend to: what a frame index means
when a node's inputs are two videos of different lengths, and whether a graph
may have more than one root at all — `Project.source` is singular and
`source_key` calls itself the ancestor of every root. This ADR says what an
input *is*. The index domain is a separate decision with its own trigger.
