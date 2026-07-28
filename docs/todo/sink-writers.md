---
title: Sink writers
status: deferred
after: [materialization]
opened: 2026-07-25
gated_on: >
  the first filter that emits a TableSpec (a detector producing coordinates),
  or materialization landing and needing somewhere for a compacted array
reads:
  - src/sieve/core/pipeline_model.py
  - src/sieve/cli/run_cmd.py
  - docs/SCAFFOLD.md
---

# Sink writers

**Why not now.** `Sink` has been on `Project` since the artifact landed and
nothing writes one, so `sieve run` refuses a project that declares outputs
rather than running it and silently writing nothing. That refusal is the right
behaviour and it is also the whole cost of the gap, which is small. What makes
writing the writers premature is that the two formats worth having want
different things that do not exist: VISION step 1's "coordinates as a csv" is a
table sink, and no filter emits a `TableSpec` — the one filter downsamples
frames — while an array sink writing frames back out is compaction, which is
`materialize.py`'s question about Zarr layout rather than a format choice.
Writing a parquet writer now means designing a schema against zero producers.

**What would make it the right time.** Either the first filter that emits a
`TableSpec` — a detector, a thresholder producing coordinates — or
materialization landing and needing somewhere for a compacted array to go. The
first is the likelier trigger and is the one VISION step 1 is blocked on.

Read: `src/sieve/core/pipeline_model.py` `Sink`, `src/sieve/cli/run_cmd.py`
`_refuse_sinks`, `docs/SCAFFOLD.md` `src/sieve/observe/results.py`.
