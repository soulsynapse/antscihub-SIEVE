---
title: HPC handoff, and review mode
status: deferred
opened: 2026-07-27T15:01:34-07:00
priority: unassessed
after: [sink-writers]
gated_on: >
  for HPC, a dataset that does not fit in a local session plus at least one
  sink — a real user with a real cluster, not a milestone; for review mode, the
  first durable output worth interpreting, which is the same trigger the
  deferred **Coverage and detection lanes** item has
reads:
  - docs/SCAFFOLD.md
  - docs/VISION.md
  - docs/todo/sink-writers.md
---

# HPC handoff, and review mode

Both are readers of durable outputs and there are none — `sieve run` refuses a
project that declares a `Sink`, so a cluster job would produce nothing to bring
home and a review tool would open nothing. They share that one gate, which is
why they share an entry.

**HPC is not a special path**, and this does not need revisiting: it consumes
the same serialized DAG the CLI does, which is what rule 2 is for. `hpc/handoff.py`
is job-script generation from an artifact that already exists, not a second
executor, and its size is proportional to how many schedulers it must speak.
The resource posture follows from that and is recorded where it would be
violated — `mutual/machine.py`'s module docstring: the generated script declares
resources to the scheduler and nothing to SIEVE.

**The constraint that shapes the sweep later.** VISION's HPC wizard toggles
things like whether a compaction checkpoint happens, on the grounds that a
cluster's memory may make it unnecessary. That makes compaction a *plan*
property rather than a fact about the artifact, and an artifact that hard-codes
it is one the wizard cannot edit.

Read: `docs/SCAFFOLD.md` `hpc/` and `review/`, `docs/VISION.md` steps 6 and 7.
