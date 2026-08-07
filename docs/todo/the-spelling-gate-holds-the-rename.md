---
title: The spelling gate holds the rename
step: "01.5"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_id_spelling.py -q"
opened: 2026-08-06
---

# The spelling gate holds the rename

v2's `tests/unit/test_filter_id_spelling.py` ports as
`test_tool_id_spelling.py`, shrink-only: source under `src/sieve/` never
spells the pre-rename identifiers, with an exception list that starts empty
and only shrinks; `compat/` earns its entries in Phase 3
(`adr/compat-spells-v2.md`). The identity *values* (`"crop"`, `"detect"`, …)
are frozen and are not what this gate scans for
(`adr/tools-not-filters.md`). The docs-side twin already runs
(`dead_language` in `scripts/doc_index.py`); this one covers identifiers,
which the docs gate deliberately leaves to it.
