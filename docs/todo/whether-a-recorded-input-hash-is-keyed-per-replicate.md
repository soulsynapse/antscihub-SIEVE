---
title: Whether a recorded input hash is keyed per replicate, since a path is a deviable parameter
status: deferred
deferred_for: decision
gated_on: whether the document should be able to claim which file a replicate that deviates a path parameter reads, or whether a deviated external input is deliberately unclaimed
priority: normal
phase: "03"
opened: 2026-08-09
---

# Whether a recorded input hash is keyed per replicate, since a path is a deviable parameter

`Project.input_hashes` is `dict[str, str]` — node id to `content_hash` — and its
field comment argues the keying from the thing that breaks it: keyed by node
"because the path is already a parameter and resolves per replicate; what is
being claimed is what a *node* reads." Resolving per replicate is exactly the
condition under which one node reads two files in one run. `Replicate.overrides`
is sparse over arbitrary parameter names and asks nothing about stereotype, so a
path parameter is deviable like any other, and one slot cannot hold two claims.

`a50027a` made it observable by adding the only caller: `run_cmd._external_inputs`
calls `check_input_hashes` once per replicate with that replicate's resolved
files, so at most one replicate can match the recorded hash and every other is
refused. Measured in
[a node-keyed input hash refuses the replicate that deviates its path](../findings/2026.08.09-a-node-keyed-input-hash-refuses-the-replicate-that-deviates-its-path.md);
the remedy the refusal message gives — re-record deliberately — moves the
refusal to the other replicate rather than clearing it.

**No `done_when`, because the shape is a decision and not an implementation.**
Two forms are live. Key by `(node, replicate)` with the node-level entry as the
inherited default, which mirrors `Replicate.overrides`' own two-level sparsity
and makes the claim exactly as specific as the parameter it is about; or rule
that a claim is about the node's own parameters and a replicate that deviates a
path drops the claim for itself, which costs nothing in schema and leaves the
deviated file unclaimed. The first is a schema change and a migration; the
second is a sentence and a narrowing of `check_input_hashes`. Which is right
turns on whether a deviated external input is a thing the document should be
able to make a promise about, and that is Kendrick's.

**Nothing waits on it.** No caller of `Project.with_input_hash` exists under
`src/`, so no project can carry an entry, and the scenario that would exercise
the gap — an A/B of two backgrounds — was ruled out of VISION on 2026-08-08 by
[whether VISION's picker scenario states an A/B](whether-vision-states-the-background-ab.md)
and sits in PLAN.md's revival table. The gap is what will be waiting on the day
that paragraph returns, or the day a front end learns to record a hash,
whichever is first. It is filed now because the argument is cheap while the code
is one commit old and expensive once a document in the wild carries entries.
