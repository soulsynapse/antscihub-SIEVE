---
title: Sink writers, and the replicate status that reads them
status: deferred
after: [materialization]
opened: 2026-07-25
gated_on: >
  the first filter that emits a TableSpec (a detector producing coordinates),
  or materialization landing and needing somewhere for a compacted array
reads:
  - src/sieve/core/pipeline_model.py
  - src/sieve/cli/run_cmd.py
  - src/sieve/pipeline/executor.py
  - docs/SCAFFOLD.md
  - docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md
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

## The replicate status columns, which are the first reader

Folded in from a separate entry 2026-07-28: it was gated on this item landing
"or materialization — the same trigger, from either end", which makes it this
item's downstream half rather than a peer.

REFINED-VISION's replicate section asks the full-width table to be "the
replicate status ... the progress bar for the crop, at the very least, and the
list of outputs defined by the DAG, and whether they exist". Both halves are
readings of a filesystem nothing writes to, so an existence column would report
"missing" for every row forever — a widget that can only ever be wrong in one
direction.

The crop half is not merely unwritten, it is a bar for a job that does not
exist. The crop is applied per frame at the graph's root in memory
(`pipeline/executor.py`), and a materialized crop is a `Project.checkpoints`
entry — contractually never hashed, deliberately optional. A progress bar
implies a background task with a duration; what actually happens when a user
accepts a replicate is a render submission. See
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`.

**The half that is derivable today, and is deliberately not being built
alone.** "The output list is defined by what the different steps of the dag
announce they can produce" is `FilterSpec` declarations over `Dag.order`, and
needs nothing new. A column listing what *could* be produced, beside no
statement of what *has* been, is the weaker of the two claims and the one users
will read as the stronger — so it waits and arrives with its other half.

Read: `src/sieve/core/pipeline_model.py` `Sink`, `src/sieve/cli/run_cmd.py`
`_refuse_sinks`, `docs/SCAFFOLD.md` `src/sieve/observe/results.py`.
