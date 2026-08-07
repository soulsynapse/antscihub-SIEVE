---
title: The committed tree fails `ruff format --check`, and ruff is unpinned
status: open
gated_on: nothing
priority: normal
opened: 2026-08-07
---

# The committed tree fails `ruff format --check`, and ruff is unpinned

`uv run ruff format --check .` reports `src/sieve/pipeline/executor.py`
(a ternary ruff 0.16.1 now wants on one line) and
`tests/unit/test_tool_contract.py` (a missing blank line before `probe_run`) as
unformatted. Both were committed formatted, so the formatter moved under them:
`pyproject.toml` lists `"ruff"` with no bound, and every environment resolves
whatever is newest that day.

The count is now five, not two: `tests/integration/test_crop_serving.py`,
`tests/integration/test_checkpoints.py`, and `tests/unit/test_crop_binding.py`
joined it as Phase 05 landed them, each with the same shape — a wrapped call
the new formatter collapses onto a line that lands at exactly the 100-char
limit. That is the growth this item predicted: every file written against the
version a session happened to resolve is a file the next version may disagree
with, so the number rises with the tree rather than staying at whatever a
reformat left it.

Reformatting today's files fixes today's report and not the cause — the next
release picks different files, and the first session to notice pays for it
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

One adjacent question for whoever takes this, because it is the same kind of
gap and cheaper to answer here than to mint separately: `mypy` is not in the
dev group at all, so nothing in v3 type-checks. That is a larger decision than
a formatter pin — it is whether v3 gates on types — and it may want its own
item, but it should not be discovered a fourth time by someone reading this one.

Found during 03.7.1, which touched neither file. Minted four times now, under
four slugs, by 03.7.1's two attempts, by 04.3, and by 05.3's re-take — see
`docs/findings/loop/2026.08.07-the-pool-is-not-read-before-an-item-is-minted-into-it.md`.
