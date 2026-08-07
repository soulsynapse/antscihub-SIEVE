---
title: The executor ports verbatim and honors lookahead
step: "02.3"
status: deferred
gated_on: "02.2 — `executor.py` imports `ExecutionPlan` from `pipeline/plan.py`,
  which 02.2 was to build and did not, and it imports `backend/dispatch.py` and
  `pipeline_model.Node` besides, so it carries two of 02.2's three blockers
  before its own extension is reached"
done_when: "uv run pytest tests/unit/test_executor.py tests/unit/test_stateful_execution.py -q"
opened: 2026-08-06
---

# The executor ports verbatim and honors lookahead

`pipeline/executor.py` verbatim plus the one reviewed extension: emission
delayed by declared lookahead, a centered window being warmup + lookahead
(PLAN.md, Phase 2). The extension is the only non-verbatim hunk in the diff —
anything else the diff shows is a mistake by definition. State stays minted
per run from the spec-declared factory and branching stays on declared shape,
never `tool_id` (`adr/no-kernel-apparatus.md`). New emission-delay tests join
`test_executor.py` with `lookahead` in their names.

Added at 01.2's review, 2026-08-07: **`run` joins `ToolSpec` here.** 01.2 cut
it — declared-means-verified refuses a field whose only reader is two phases
out — so ADR-2's "the spec points at it" is unimplemented, and this is the
step whose reader makes it implementable. Without the field the executor has
to find a tool's `run` by its id, which is precisely the file-that-grows-with-
the-tool-count ADR-2 exists to prevent, and a verbatim port of v2's executor
would carry `backend/dispatch.py`'s scaffolding across to fill the gap.

Deferred at 02.2's review, 2026-08-07, without a work run: `executor.py`'s six
`sieve` imports resolve to `backend.dispatch` (dropped), `core.pipeline_model`
(Phase 3, re-derived), `pipeline.cache` (named nowhere in PLAN.md's port
disposition, the same gap `core/replicates.py` has), and `pipeline.plan`
(02.2, deferred). That is not a phase-order judgement a reviewer is making, it
is the dependency arithmetic — the item's input does not exist because the
step before it stopped. `gated_on` names 02.2 rather than the three rulings,
because clearing 02.2 clears this too. The reasoning for deferring it here
instead of spending a work run to rediscover it is
`findings/loop/2026.08.07-a-deferral-propagates-and-only-the-review-sees-it-coming.md`.
