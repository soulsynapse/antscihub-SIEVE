---
title: The materialize command derives what v2 was handed
priority: high
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# The materialize command derives what v2 was handed

`materialize_crop` landed with 05.1 and nothing calls it. PLAN.md's "Then the
commands" paragraph names `materialize` among the `cli/` ports, but no item in
this index builds it, so the artifact is currently uncreatable outside a test —
which is O3's whole subject, headless creation, unmet.

It is not a transcription. v2's `materialize_cmd` read a `ClipRange` off the
project and an `roi` off the replicate; schema v1 has neither. The region is a
per-replicate override of a crop node's `region` parameter
(`adr/detector-is-a-node.md`) and the span is the `span` tool's parameters in
the graph, so the command's real work is deriving both from the document and
refusing clearly when it cannot — a graph with no crop node at the root, a
replicate that overrides nothing, two crop nodes and no way to choose. `luma`
is `not Dag.needs_chroma`, which the command must ask the graph rather than
accept as a flag.

Registration is the half that is easy to leave out and expensive to notice: an
artifact nothing points at is minutes of decode the next session silently pays
again, so the command saves the project with `with_crop` and the case asserts
`backs` against the reloaded document.

Wants 05.2 first — `resolve_source` is what makes a registered record mean
anything on the next run, and a command that writes records nothing reads is
half a feature. Not a step for that reason: it follows 05.2 and 05.3 rather
than blocking them.

`findings/2026.08.07-05.1s-case-count-is-v2s-file-count-and-two-of-them-are-the-command.md`
is why this is a separate item rather than the tail of 05.1.
