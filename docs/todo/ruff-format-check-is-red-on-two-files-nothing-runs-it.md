---
title: ruff format --check is red on two files, and nothing runs it
status: open
priority: normal
gated_on: nothing
opened: 2026-08-07
---

# ruff format --check is red on two files, and nothing runs it

`uv run ruff format --check .` fails on `src/sieve/pipeline/executor.py:481`
(a ternary the formatter wants on one line) and
`tests/unit/test_tool_contract.py:751` (a missing blank line). Both are
pre-existing at 23501dd and neither was touched by 03.7.1; `ruff check` is
clean, which is why this has gone unnoticed — the two commands disagree and
only the first one gets run by habit.

The fix is `uv run ruff format .`. The reason it is an item rather than a
drive-by is the second half: nothing in the tree runs `format --check`, so it
will go red again the same way. v2 gated it in a nox session
(`noxfile.py`, `lint`), which v3 has deliberately not ported — this is the
first thing that has needed it, so the porting decision belongs with whoever
takes this.
