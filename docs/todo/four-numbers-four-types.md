---
title: Four kinds of number, four types
status: open
opened: 2026-07-29T12:18:58-07:00
priority: high
gated_on: nothing
reads: [src/sieve/core/types.py, src/sieve/core/filter_base.py]
---

# Four kinds of number, four types

REWORK.md R6's foundation, and the first of its four ordering constraints:
these types land before anything is fitted or measured, or the fits are
redone.

Media time (on rational fps — `Fraction`, because 30000/1001 drifts over a
two-hour recording and `ParamsBase.output_rate` already records why), wall
time, work units, and frame counts become four types in `core/types.py` with
no implicit conversion between any two. Pyright strict is the gate — the same
mechanism that made `workers` a required argument, firing where the violation
is written.

The distinctions that are load-bearing:

- **Work units never wear a time-flavored name.** The moment something calls
  one `estimated_ms`, the anchor is gone.
- **Frames are node-relative, not a duration.** Warmup is counted in a
  filter's own *input* frames, and a rate-changing node between two others
  makes them speak different index spaces — folding frames into media time
  erases exactly the arithmetic `source_warmup_frames` exists to get right.
- These are agreement vocabulary by R4's own test (two implementations must
  agree on what a media time is to interoperate), so they live in `core/` and
  do not wait on `the-mutual-tier` — they are not going to move.

Scope: the types and their arithmetic, plus migrating the obvious signatures
(`Budget.limit_ms` stays; wholesale budget re-denomination is
`ceilings-in-the-dimension-they-bound`). Keep the first landing small enough
that pyright's errors are the work list, not a flag day.
