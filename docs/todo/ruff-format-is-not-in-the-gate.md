---
title: ruff format is not in the gate, and two files have already drifted from it
status: open
gated_on: nothing
priority: normal
opened: 2026-08-07
---

# ruff format is not in the gate, and two files have already drifted from it

`.github/workflows/ci.yml` runs `ruff check`, `lint-imports`, and `pytest`, and
its own comment says it is "character-for-character what a commit is checked
against locally". `ruff format --check .` is in neither place, so nothing has
ever asserted the formatting, and as of 04.3 two files disagree with it:
`src/sieve/pipeline/executor.py` (a wrapped conditional the formatter joins)
and `tests/unit/test_tool_contract.py` (a missing blank line before a
top-level def). Both predate 04.3 and neither is a `ruff check` finding.

The decision is which way to close it: add `ruff format --check` to the gate
and reformat the two files, or decide formatting is not gated here and say so
where the CI comment currently implies one list covers everything. Doing the
first quietly inside another item is what should not happen — a formatter added
to CI is a rule every future diff answers to.
