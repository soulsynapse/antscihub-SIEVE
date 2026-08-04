---
title: Presentation is a declared channel, not a switch in a widget
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
after: [the-spec-has-three-channels, a-filter-names-what-it-emits]
reads: [src/sieve/gui/chain_model.py, src/sieve/gui/wizard_model.py]
---

# Presentation is a declared channel, not a switch in a widget

Decided 2026-07-29 (REWORK.md ## Decided): captions, signal labels,
`primary_params`, and `FilterSpec.cost` live on the spec's presentation
channel — filter-owned, declared beside the parameters they describe, visibly
non-hashed (the partition test from `the-spec-has-three-channels` covers any
field the channel gains, for free).

What this deletes from `gui/`: `caption_for`'s per-filter switch,
`SIGNAL_LABELS`'s hand-typed map, and every enumeration they anchor — the
sites `a-filter-id-spelled-twice`'s exception list names. What it moves
*into* `core/`'s partition rather than out of it: nothing new — the channel
already exists; this item is consumers.

The guidance-markdown parsing in `wizard_model.py` (`parse_guidance`) is the
boundary case: the `.md` beside a filter is already the filter author's
presentation surface, so prefer extending it over growing spec fields —
whichever way this falls, decide it once here and record it in the entry.

Aspiration A3 is the quiet stake: an optimizer reading
`params_model.model_fields` and a GUI reading a hand-typed list of five names
are searching two different spaces. After this item they read the same one.
