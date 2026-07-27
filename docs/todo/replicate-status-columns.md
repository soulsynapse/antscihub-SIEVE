---
title: "Replicate status: crop progress and output existence"
status: deferred
gated_on: >
  the deferred **Sink writers** item (docs/todo/sink-writers.md) landing, or
  materialization — the same trigger, from either end
reads:
  - src/sieve/gui/replicate_table.py
  - src/sieve/pipeline/executor.py
  - docs/REFINED-VISION.md
---

# Replicate status: crop progress and output existence

**Why not now.** REFINED-VISION's replicate section asks the full-width table to
be "the replicate status ... the progress bar for the crop, at the very least,
and the list of outputs defined by the DAG, and whether they exist". Both halves
are readings of a filesystem nothing writes to. There is no
`pipeline/materialize.py`, `Sink` is a declaration with no writer, and
`cli/run_cmd.py` *refuses* a project that declares outputs rather than running
it — so an existence column would report "missing" for every row forever, which
is a widget that can only ever be wrong in one direction.

The crop half is not merely unwritten, it is a bar for a job that does not
exist. The crop is applied per frame at the graph's root in memory
(`pipeline/executor.py`), and a materialized crop is a `Project.checkpoints`
entry — contractually never hashed, deliberately optional, and absent. A
progress bar implies a background task with a duration; what actually happens
when a user accepts a replicate is a render submission. See
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`.

**What would make it the right time.** The deferred **Sink writers** item,
docs/todo/sink-writers.md, landing, or materialization — the same trigger, from
either end. At that point outputs have a path, a write has a duration, and both
columns become readings rather than guesses.

**The half that is derivable today, and is deliberately not being built alone.**
"The output list is defined by what the different steps of the dag announce they
can produce" is `FilterSpec` declarations over `Dag.order`, and needs nothing new.
A column listing what *could* be produced, beside no statement of what *has*
been, is the weaker of the two claims and the one users will read as the
stronger — so it waits and arrives with its other half.
