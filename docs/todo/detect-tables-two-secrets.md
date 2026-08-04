---
title: detect/tables.py hides two secrets
status: open
priority: unassessed

gated_on: >
  nothing structurally

reads:
  - src/sieve/detect/tables.py
  - tools/docstring_audit.py
---

# detect/tables.py hides two secrets

Flagged by the docstring-convention sweep rather than brought to it. Measured:
782-word module docstring against a 250 cap, 16 symbol docstrings (896 words),
1954 words of prose total against a 400 cap — the worst overage found so far,
larger even than `player.py`'s prior flag.

**Secret one: a verified CSV write is generic and belongs to no detector.**
`Column`, `write_table`, `_verify`, and `TableVerificationError` know nothing
about detection — they are "declare name/meaning/getter once, write, read the
file back, rename over the target, delete the partial on failure." That
mechanism is rule 8's write-then-verify pattern applied to CSV specifically,
and nothing in it mentions a frame, an interval, or an element.

**Secret two: what a detection row means, and how it stays honest under rule
6.** `series_columns`, `INTERVAL_COLUMNS`, `_detected`, `_measured`,
`_fraction`, `_seconds`, `_nonfinite`, `_band`, `_readme`, and the
`DetectionExport`/`Frame`/`Interval` dataclasses are all about this one
detector's export: which columns exist, why the noun comes from the graph
(`ElementKind`) rather than being a literal, why disarmed writes no
`intervals.csv` at all, why non-finite values are spelled `Inf`/`NaN` and
absence is spelled `NA`, why the derived columns are rounded but the measured
ones print at exact `float32` precision, and why there is no `settled` column.
This is a single coherent secret — "the detection export contract" — but it is
long *because* it is rule-6-load-bearing: each paragraph is a way the file
could look more or less founded than it is, and the file's own convention
(comments survive only when they record a decision, a rejected alternative, or
a failure mode with no trace) is what is generating the length. This half
alone would very likely still be over a 250-word docstring cap on its own —
it was not measured in isolation before writing this entry.

**Co-change check does not apply.** The candidate halves have never existed as
separate files; there is no split to measure history against, only a single
file's git log. Recommending a split from present content rather than from
observed churn is the honest position here — it is not backed by the
`git log` evidence CLAUDE.md's split section asks for.

**Recommendation**: split the generic writer (`Column`, `write_table`,
`_verify`, `TableVerificationError`) out from the detection-specific column
declarations and README generation, into a new module in a generic layer —
`write_table` has no detection-specific import today, so it is not
layer-locked to `sieve.detect`. That leaves `tables.py` holding one secret
(the detection export contract) at a size that may still need a documented
exemption similar to the three contract modules, given how much of the
remaining content is genuinely underivable rule-6 reasoning. Both the new
module's name and the exemption question are calls for whoever owns the
split, not something to force through the mechanical cap.
