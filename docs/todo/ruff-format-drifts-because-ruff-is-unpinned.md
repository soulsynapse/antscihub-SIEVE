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

A pin is only half of it: nothing in v3 runs `format --check` at all, which is
why this went unnoticed for two commits while `ruff check` stayed green — the
two commands disagree and only the second one gets run by habit. v2 gated the
formatter in its `lint` nox session, which v3 has deliberately not ported.
This is the first thing that has needed it, so the porting decision belongs
with whoever takes this.

One more thing whoever takes this has to reconcile: `.github/workflows/ci.yml`
runs `ruff check`, `lint-imports`, and `pytest`, and its own comment calls that
list "character-for-character what a commit is checked against locally". Adding
`format --check` in one place and not the other makes that comment false, so
either it moves into both or the comment has to stop claiming one list covers
everything.

Found during 03.7.1, which touched neither file. Minted three times now, under
three slugs, by 03.7.1's two attempts and by 04.3 — see
`docs/findings/loop/2026.08.07-the-pool-is-not-read-before-an-item-is-minted-into-it.md`.
