---
title: The cache-key golden offers two remedies and there are three ways to move it
priority: low
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_declarations_run.py -q -k a_reshaped_params_model_moves_the_key_without_a_version_bump"
opened: 2026-08-08
---

# The cache-key golden offers two remedies and there are three ways to move it

`test_a_version_bump_moves_the_key`'s failure message names two causes for a
moved digest: the tool changed what it computes, in which case the version moves
and the golden is replaced, or a key position moved, in which case
`HASH_VERSION` is the remedy. 07.1 hit a third — `span`'s two bounds became one
pair-shaped `frames` parameter, so the canonical params JSON the key folds
changed while the frames the tool selects did not.

Neither offered remedy is right for it. Bumping the version invalidates entries
for a computation that is unchanged, and moving `HASH_VERSION` invalidates every
tool's. What is right is replacing the digest at the same version, and the
reason it is safe is a property of the model rather than of the tool:
`ParamsBase` sets `extra="forbid"`, so a document written with the old field
names is refused on load rather than read as something else. A reader who does
not know that reaches for one of the two sledgehammers the message does offer,
and the larger one flushes the whole store.

So the message is short one clause, and the case wants an assertion rather than
only prose: a params model reshaped without a changed computation keys
differently at the same version, and the document that names the old fields does
not load. The `done_when` names that case in
`tests/unit/test_declarations_run.py`, beside the golden it explains.
