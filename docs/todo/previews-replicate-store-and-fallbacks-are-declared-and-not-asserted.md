---
title: Preview's replicate, store and fallbacks are declared and not asserted
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# Preview's replicate, store and fallbacks are declared and not asserted

A reviewer's 23-mutant sweep over 06.2 left five survivors
(`docs/findings/loop/2026.08.07-two-replicates-that-differ-only-in-name-cannot-tell-a-flag-from-its-label.md`).
Four are worth a case; the fifth is `_header`'s singular/plural and is not.

**The replicate never reaches a render that could show it.**
`ExecutionPlan.build(replicate=None)` in `PreviewSession._plan` passes all 13
cases. `test_the_named_replicate_is_the_one_previewed` builds two replicates
with no `overrides` between them, so the flag's whole observable effect is the
name in the header line; the edit case pins an override and still cannot see it,
because `with_param_edit` moves the node default alongside the pin. The case
needs a replicate whose override alone changes what is computed — two
replicates deviating on `tail.factor`, rendered in turn against one store, where
the second is not a total cache hit. That is also the assertion `_target`'s
docstring is written against: previewing the undeviated graph is the failure.

**An injected store is indistinguishable from the default one.** Dropping the
`store` argument on the constructor passes, because both callers hand it a fresh
`MemoryFrameStore`. The argument exists so a caller can keep a store across
sessions — the reason `set_replicate`'s docstring gives for rebuilding a session
over a written crop — so the case is one store handed to two sessions, with the
second render serving from the first session's entries.

**`PreviewRender.reuse` on an empty tally.** The docstring argues that reporting
1.0 would make an empty graph the best-performing row in a table; returning 1.0
passes. A `Pipeline` with no nodes rendered over a window is the case, if the
document model permits one — if it does not, the branch is unreachable and the
right edit is to say so rather than to return a number.

**`--edit`'s bare-word value.** `_parse_edits` falls back to the literal string
on a `JSONDecodeError` so that `mode=fast` works without shell-quoted JSON;
`raise` in place of the fallback passes, because every `--edit` in the file
passes a JSON integer. No tool on the shelf takes a string parameter yet, so the
case may have to wait for one — which is itself worth knowing, since the
fallback's justification is written about a tool that does not exist.

## Folded 2026-08-10 at review: the re-aimed session is now the window's path

`the-loop-draws-the-baseline-while-the-fan-stands-on-a-region.md` settled that
the window re-aims its live session (`TuningLoop.set_replicate` forwarding here)
rather than rebuilding it, and it settled it *on* the store: the item's reason
for preferring re-aim is that clicking back onto a region a user has already
seen is a cache hit, which a rebuild would throw away. Nothing asserts that.
Its own case asserts only that two aims produce two pictures, and that stays
true of a rebuild.

So the first clause above — "two replicates deviating on `tail.factor`,
rendered in turn against one store, where the second is not a total cache hit" —
is no longer only about `PreviewSession` in the abstract; it is the shape the
GUI now depends on, and the assertion it is owed has a second half: the *first*
replicate's entries survive the re-aim, so the click back serves rather than
recomputes. That is the difference between the two designs, and it is the only
thing in the tree that would notice a later hand swapping them.
