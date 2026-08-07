---
title: The materialize command derives what v2 was handed
step: "05.12"
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_materialize.py tests/integration/test_cli_help.py -q"
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

Last of the four, and each predecessor is a real dependency rather than a
preference. 05.2 is what makes a registered record mean anything on the next
run, and a command that writes records nothing reads is half a feature. 05.10
derives the region per replicate and is the one that puts that derivation
where this can call it. 05.11 is the naming collision: this command is what
makes it reachable, so shipping this first would ship the corruption.

It was a pool item on the reasoning that following 05.2 is not the same as
blocking it. True, and beside the point — the pool orders by priority and then
by filename, which cannot say "after", and put this ahead of the item that
gates it.

`findings/2026.08.07-05.1s-case-count-is-v2s-file-count-and-two-of-them-are-the-command.md`
is why this is a separate item rather than the tail of 05.1.
