---
title: HPC handoff, and review mode
status: deferred
gated_on: >
  for HPC, a dataset that does not fit in a local session plus at least one
  sink — a real user with a real cluster, not a milestone; for review mode, the
  first durable output worth interpreting
reads:
  - docs/SCAFFOLD.md
  - docs/VISION.md
  - docs/todo/sink-writers.md
---

# HPC handoff, and review mode

**Why not now.** Both are readers of durable outputs and there are none. `sieve
run` refuses a project that declares a `Sink`, so a job that ran on a cluster
would produce nothing to bring home and a review tool would open nothing. These
are downstream of the deferred **Sink writers** item,
docs/todo/sink-writers.md, and of materialization, and are listed together
because they share that one gate.

The architectural decision they rest on is already made and does not need
revisiting: HPC is not a special path. It consumes the same serialized DAG the
CLI does, which is what non-negotiable #2 is for. So `hpc/handoff.py` is job
script generation from an artifact that already exists, not a second executor,
and its size is proportional to how many schedulers it must speak rather than to
anything about SIEVE.

**What would make it the right time.** For HPC: a dataset that does not fit in a
local session, plus at least one sink. VISION is explicit that most projects
will not need it and that the requirement is only that SIEVE be *ready* — so the
trigger is a real user with a real cluster, not a milestone. For review mode:
the first durable output worth interpreting, which is the same trigger the
deferred **Coverage and detection lanes** item,
docs/todo/coverage-and-detection-lanes.md, has.

**Worth recording now**, because it constrains the sweep design later: VISION's
HPC wizard toggles things like whether a compaction checkpoint happens, on the
grounds that a cluster's memory may make it unnecessary. That makes compaction a
*plan* property rather than a fact about the artifact, and an artifact that
hard-codes it is one the wizard cannot edit.

Read: `docs/SCAFFOLD.md` `hpc/` and `review/`, `docs/VISION.md` steps 6 and 7,
the deferred **Sink writers** item, docs/todo/sink-writers.md.
