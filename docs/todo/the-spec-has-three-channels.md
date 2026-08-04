---
title: The spec has three channels, and every field is in exactly one
status: open
opened: 2026-07-29
priority: high
gated_on: nothing
reads: [src/sieve/core/filter_base.py, src/sieve/pipeline/cache_key.py]
---

# The spec has three channels, and every field is in exactly one

REWORK.md R5 at the spec, and the honest gate for "core carries no GUI
policy" — `primary_params` is a field, not an import, so no import contract
can see it; a declared partition can.

`core/filter_base.py` gains a `Channel` enum (identity / execution /
presentation) and a `SPEC_CHANNELS` mapping placing every `FilterSpec` field
in exactly one. Today's classification: `cost` and `primary_params` are
presentation; `mode`, `rate_changing`, `warmup_frames`, `stateful`,
`deterministic` are execution; `filter_id`, `version`, `params_model`,
`accepts`, `emits`, `element`, `backend_agnostic` are identity.

Three tests in `tests/unit/`, each failing for a distinct reason:

1. The partition is total and exact, both directions — a new field with no
   channel fails at the moment it is written, which is what catches the next
   `primary_params`.
2. A presentation edit moves no cache key: for each presentation field, build
   a one-node plan, mutate the field, assert `node_key` unchanged. This is
   ARCHITECTURE.md rule 7's own named gap ("no test toggles a checkpoint and
   asserts every key survives") in its generalized form.
3. `register_filter`'s signature equals `FilterSpec`'s field list — the
   hand-maintained second copy ARCHITECTURE.md §3 calls "one field addition
   away from drifting silently", closed with `inspect.signature`.

Decided 2026-07-29 (REWORK.md ## Decided): presentation hints *will* live on
this channel — `caption_for`, `SIGNAL_LABELS`, `primary_params`, and `cost`,
one answer for all four. Moving the GUI's copies onto it is
`presentation-is-a-channel-not-a-switch`, not this item; this item only makes
the destination exist and provably non-hashed.
