---
title: Work units have one anchor and no coefficient table
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
after: [four-numbers-four-types]
serves: A2
reads: [src/sieve/core/filter_base.py, src/sieve/cli/inspect_cmd.py]
---

# Work units have one anchor and no coefficient table

`CostEstimate.seconds_per_megapixel` fuses a work term and a machine term
into one scalar — a hand-typed constant "on the reference CPU", consumed only
by `sieve inspect`, producible by nothing. The same dataclass already does it
right once: `peak_bytes_per_input_byte` is dimensionless, relative,
composable.

Cost becomes `WorkUnits` anchored to one reference operation (a full-frame
copy at reference resolution), Postgres-style: one anchor, everything
relative, conversion left to calibration. **No per-filter measured
coefficient table** — the known failure of this design is an uncalibrated
installation producing numbers that are internally consistent and externally
meaningless, and the per-filter table is how it happens.

The declared cost moves to the spec's presentation/execution side per
`the-spec-has-three-channels`' partition (it is filter-owned, not interop
vocabulary — REWORK.md ## Decided). An uncalibrated machine yields work units
that say so; it never falls back to someone else's constants.
