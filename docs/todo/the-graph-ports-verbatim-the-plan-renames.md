---
title: The graph ports verbatim; the plan renames
step: "02.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_dag.py tests/unit/test_cache_key.py tests/unit/test_plan.py -q"
opened: 2026-08-06
---

# The graph ports verbatim; the plan renames

`pipeline/dag.py` and `cache_key.py` verbatim; `plan.py` port-with-rename
(PLAN.md, porting discipline). The cache-key test ports unchanged — the
identity values are frozen (`adr/tools-not-filters.md`), so what enters a key
means the same thing it meant in v2. A key that changes for any reason other
than the field rename itself is a stop-and-write blocker, not a constant to
update.
