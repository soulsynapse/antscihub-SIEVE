---
title: An input's origin is a fact about its key
adr: 18
position: "04.04"
status: settled
decided: 2026-08-07
amended: 2026-08-07
---

Every input carries an identity that enters the key; naming an upstream node or
a user-chosen file changes only how that identity is derived, never the
executor's route or the payload's kind.

What an input *carries* is a separate and open question. `StreamKind` answers it
today with arrays and tables — `detect` consumes a signal series and not frames
— and a third kind arrives when a tool cannot be expressed in two, under the
rule that governs every closed vocabulary here
([a-tool-is-one-file](a-tool-is-one-file.md)). Frames are the important case for
video and they are not the general one. `executor.FrameSource` — `read(index) ->
Frame`, satisfied by a `VideoReader`, by a reader over a materialized crop, and
by a list of frames in a test — is the *fetch* shape for one payload kind, and
this ADR is not about it. How an input is fetched, and whether it is indexed per
frame at all or is one value for the whole run, is a third axis this does not
decide either.

Why the identity half is worth deciding on its own: v3 has built the
substitution twice, each time for a single case. A written crop "is a child
source with its own identity, not the parent's" (`core/pipeline_model.py`), and
the executor serves it where it would otherwise have run `crop`. A checkpoint
is the same move in the other direction, and Phase 5's gate is that a rerun
reading written artifacts equals the run that computed them *with every cache
key unmoved* ([PLAN.md](../PLAN.md)). Both are already interchangeable with a
computed input below the key; what is missing is that a tool cannot ask for one.
The alternative — a second input concept with its own route through the executor
— is what [one-execution-path](one-execution-path.md) refuses on the
preview/production axis, and for the same reason: with two routes, the one that
was tuned against is not the one that runs.

Derivation is the whole of the difference. An upstream input's key is computed
from the graph, so an edit propagates. A user-designated file has nothing
upstream to constrain it, so its key comes from the file's own content identity
— `source_key` and `decoder_identity()` exist for exactly that. The failure this
prevents is not hypothetical: saving two background models and swapping them to
see which detects better is an ordinary tuning action, and a swap the key cannot
see serves the first model's results under the second's name. Well-formed key,
plausible frame, no symptom.

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

What this does not settle: what a frame index means when a node's inputs are
two videos of different lengths, and whether a graph may have more than one root
at all — `Project.source` is singular and `source_key` calls itself the ancestor
of every root. The index domain is a separate decision with its own trigger.
