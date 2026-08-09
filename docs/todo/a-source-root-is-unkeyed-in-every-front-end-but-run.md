---
title: A source root is unkeyed in every front end but run
status: open
gated_on: nothing
priority: high
phase: "03"
done_when: "uv run pytest tests/unit/test_preview.py tests/integration/test_materialize.py -q -k picked"
opened: 2026-08-09
---

# A source root is unkeyed in every front end but run

`Dag.node_keys` skips a source-tool node whose identity is not in `picked` —
`continue`, not an error — and a skipped node takes its whole subtree with it,
because every node below reads `keys[parent]` and finds nothing. `cli/run_cmd.py`
resolves the identities at run start and passes them; `pipeline/preview.py` and
`cli/materialize_cmd.py` build plans with no `picked` at all. So a pipeline with
a `pick` root caches nothing in a preview, and a drag recomputes the whole chain
every frame — the interactive loop `CLAUDE.md` names as the product constraint,
not an efficiency note.

Minted at the 2026-08-09 review that deferred
[crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md),
which had folded this observation in on the argument that whichever shape that
item picked would answer it. That item is now deferred on an ADR-level ruling
about key flavours, and this gap does not depend on that ruling: it is live for
`pick` today, with no crop or artifact involved. The fold's paragraph stays where
it is — what belongs to that item is what a *served crop* root has to know, and
that is still its call.

The shape is open and is this item's to settle: a shared run-start step the three
front ends call, or a `picked` argument each threads. The criterion names the two
front ends and not a spelling, and must fail while either builds a plan whose
source root is unkeyed — asserting `run_cmd`'s behaviour again does not satisfy
it.

Worth deciding alongside: whether `node_keys` should keep silently dropping a
source node with no identity. The `continue` is right for a node that is
genuinely uncacheable, but here it converts a caller's omission into a silent
performance cliff with no symptom, which is the same shape as the wrong-answer
failure `cache_key.py` opens against — one register quieter.
