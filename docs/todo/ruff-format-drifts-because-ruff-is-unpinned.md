---
title: Two committed files fail `ruff format --check`, and ruff is unpinned
status: open
gated_on: nothing
priority: normal
opened: 2026-08-07
---

# Two committed files fail `ruff format --check`, and ruff is unpinned

`uv run ruff format --check src tests` reports `src/sieve/pipeline/executor.py`
(a ternary ruff 0.16.1 now wants on one line) and
`tests/unit/test_tool_contract.py` (a missing blank line before `probe_run`) as
unformatted. Both were committed formatted, so the formatter moved under them:
`pyproject.toml` lists `"ruff"` with no bound, and every environment resolves
whatever is newest that day.

Reformatting the two files fixes today's report and not the cause — the next
release picks two different files, and the first session to notice pays for it
again. Pin ruff to a version in the dev dependency list and reformat against
that pin in the same commit, so the check means "this tree matches the
formatter we chose" rather than "this tree matches whatever resolved".

Found during 03.7.1, which touched neither file.
