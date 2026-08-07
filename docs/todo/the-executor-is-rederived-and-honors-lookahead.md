---
title: The executor is re-derived and honors lookahead
step: "03.6"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_executor.py tests/unit/test_stateful_execution.py -q"
opened: 2026-08-06
---

# The executor is re-derived and honors lookahead

`pipeline/executor.py` re-derived against schema v1 under PLAN.md's
re-derivation clause, plus the one reviewed extension: emission delayed by
declared lookahead, a centered window being warmup + lookahead.
`tests/unit/test_executor.py` and `test_stateful_execution.py` hold **13 and
8 cases**, and this item's table has 21 rows. The algorithm is copied line for
line and the delay is the only intended change to it; `backend/dispatch.py`'s
binding is what comes out, and `Node` is schema v1's.

`pipeline/cache.py` lands here verbatim — 114 lines over `core.types`, the
store keyed by `(node key, source frame index)` that this loop writes into.
It is the one file in this item that is a byte-identical port, and its
docstring's argument for that key shape is the reason it is not re-derived
with everything else.

State stays minted per run from the spec-declared factory and branching stays
on declared shape, never `tool_id` (`adr/no-kernel-apparatus.md`). New emission-delay tests join
`test_executor.py` with `lookahead` in their names.

Added at 01.2's review, 2026-08-07: **`run` joins `ToolSpec` here.** 01.2 cut
it — declared-means-verified refuses a field whose only reader is two phases
out — so ADR-2's "the spec points at it" is unimplemented, and this is the
step whose reader makes it implementable. Without the field the executor has
to find a tool's `run` by its id, which is precisely the file-that-grows-with-
the-tool-count ADR-2 exists to prevent — and the alternative is carrying
`backend/dispatch.py`'s scaffolding across to fill the gap.

Undeferred 2026-08-07 by the phase readjustment: the blockers were
`plan.py`, schema v1 and `pipeline/cache.py`, and all three now land ahead of
this step — 02.1, 03.5, and this item respectively. The deferral was correct
arithmetic on a plan that put the graph before the schema, and the plan is
what changed.
