---
title: A claimed gate must exist, and a fired trigger must have an item
status: open
opened: 2026-07-29
priority: high
gated_on: nothing
reads: [docs/AUTO-GUARDRAILS.md, docs/REWORK.md, tools/doc_index.py]
---

# A claimed gate must exist, and a fired trigger must have an item

The two recurrences with a paid-for track record: AUTO-GUARDRAILS once wrote
"**Check:** <the test that should exist>" in the same voice for checks that
existed and checks that did not, so three unbuilt checks read as done for two
weeks; and §2's trigger fired at schema v3 with nobody noticing, so the most
valuable unwritten check stayed unwritten through the item that should have
created it. Both become test failures.

One new file in `tests/docs/`:

1. Every backticked `tests/….py::test_name` token in AUTO-GUARDRAILS.md and
   ARCHITECTURE.md resolves — AST-parse the named file and find the def/class.
   AST rather than `pytest --collect-only`: no subprocess, and it catches
   renames, which is the actual failure. (`test_doc_refs` already covers the
   path half; the `::name` half is the gap.)
2. Every cited `.importlinter` contract name resolves, via `configparser`.
3. Every `**Trigger:**` line in AUTO-GUARDRAILS parses as
   `FIRED (date) -> docs/todo/<item>` with the path resolving, or
   `NOT FIRED (re-checked date)` — a fired trigger without an item is the §2
   failure, converted.
4. Every `**Gate:**` line in REWORK.md names a resolvable test/contract or
   contains the word OPEN — which is what makes rule graduation (REWORK.md's
   *How a rule leaves this file*) visible rather than automated.

Plus one derived line in `.state.md` beside the budget line: fired-trigger
and not-fired counts with the oldest re-check date. Counts and dates read
from files only — `budget_health`'s docstring states the constraint
(nothing that moves with the clock survives a byte-exact `--check`).
