---
title: The spec has three channels, and every field is in exactly one
status: open
opened: 2026-07-29T12:18:58-07:00
priority: high
gated_on: nothing
reads: [src/sieve/core/filter_base.py]
---

# The spec has three channels, and every field is in exactly one

REWORK.md R5 at the spec, and the honest gate for "core carries no GUI
policy" — `primary_params` is a field, not an import, so no import contract
can see it; a declared partition can.

`core/filter_base.py` gains a `Channel` enum (identity / execution /
presentation) and a `SPEC_CHANNELS` mapping placing every `FilterSpec` field
in exactly one. Today's classification: `cost`, `primary_params` and `summary`
are presentation; `mode`, `rate_changing`, `warmup_frames`, `stateful`,
`deterministic` are execution; `filter_id`, `version`, `params_model`,
`accepts`, `emits`, `element`, `backend_agnostic` are identity.

**The declaration is written and uncommitted in the working tree.** What is
left is the one test that makes it load-bearing rather than a comment: the
partition is total and exact, *both directions* — every `dataclasses.fields`
name has a row, every row names a field. One test in `tests/unit/`, and the
failing direction that matters is the first: a field added without a row fails
at the moment it is written, which is what catches the next `primary_params`.

The two tests this item used to also carry are now their own items, because
neither reads `filter_base.py` and both were what made this one too big for a
single pass:
[presentation-edits-move-no-key](presentation-edits-move-no-key.md) and
[register-filter-signature-matches-spec](register-filter-signature-matches-spec.md).
The first depends on `SPEC_CHANNELS` existing; the second does not depend on
this item at all.

Decided 2026-07-29 (REWORK.md ## Decided): presentation hints *will* live on
this channel — `caption_for`, `SIGNAL_LABELS`, `primary_params`, and `cost`,
one answer for all four. Moving the GUI's copies onto it is
`presentation-is-a-channel-not-a-switch`, not this item; this item only makes
the destination exist.
