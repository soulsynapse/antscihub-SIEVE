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

## Folded 2026-08-08 — the ADR states the opposite

`adr/one-field-is-one-populated-value.md` costs the decision as "one tool's
parameters and the ported test that constructs them; the goldens are unaffected,
since the values do not move". True of the parity goldens, whose columns are
frame numbers, and false of `cache_key_span_1.0.0.txt`, which 42612df replaced —
the key folds the canonical params JSON, and reshaping the model moves that
without moving anything the tool computes. A settled ADR carrying a false
current-state claim is `CLAUDE.md`'s durable-instruction rule failing in the
place it is most load-bearing, so the sentence wants correcting to name the
cache-key golden as the one thing that does move and why replacing it at the
same version is safe. That edit is Kendrick's to make on a settled ADR; this
item is where the observation waits.

## Folded 2026-08-10 — the third cause recurred, on three goldens at once

[a-projects-directory-is-inside-every-key-below-its-source](a-projects-directory-is-inside-every-key-below-its-source.md)
excluded a source tool's path parameter from `node_key`'s params position, which
moved `cache_key_pick_1.0.0.txt`, `cache_key_footage_1.0.0.txt` and
`cache_key_checkpoint_1.0.0.txt` — every tool on the shelf that declares a
`ParamStereotype.PATH` — with no tool changing what it computes. So `span`'s
reshaped model was not a one-off: the general cause is *the derivation of the
params position changed*, of which a reshaped model and a narrowed digest are
two instances, and the message's two remedies are wrong for both in the same
way. The run replaced the three at the same version, on 42612df's precedent.

It is also the case where the safety argument the section above gives —
`extra="forbid"` refuses a document naming the old fields — does not apply,
because no field name moved and every old document still loads. The argument
that holds for both is weaker and sufficient: the new key differs from the old
one, so old entries are orphaned rather than served, and a derivation change
that *did not* move a key would be the dangerous one. Worth having in the
clause, since a reader offered only the schema argument will not find it here.
