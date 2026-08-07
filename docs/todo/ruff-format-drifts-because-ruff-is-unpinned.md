---
title: The committed tree fails `ruff format --check`, and ruff is unpinned
status: awaiting-review
phase: "00"
gated_on: nothing
priority: normal
opened: 2026-08-07
---

# The committed tree fails `ruff format --check`, and ruff is unpinned

`uv run ruff format --check .` fails on `v3` and nothing notices, because the
gate runs `ruff check` and never the formatter. The two commands read the same
`[tool.ruff]` line length and are otherwise unrelated, so green on the linter
says nothing about the formatter — which is how this survived several commits.
Meanwhile `pyproject.toml` lists `"ruff"` with no bound, so every environment
resolves whatever is newest that day and files committed formatted stop being
formatted without anyone editing them.

The file list is the evidence, because it is not stable. The first sighting was
`src/sieve/core/tool_base.py`'s `caption_unknown` comprehension, one line where
the formatter wanted three; 01.4 happened to be editing that file and
reformatted it in passing, and the report moved to `pipeline/executor.py` and
`tests/unit/test_tool_contract.py`. Phase 05 landed three more —
`test_crop_serving.py`, `test_checkpoints.py`, `test_crop_binding.py` — each the
same shape, a wrapped call the newer formatter collapses onto a line that lands
at exactly the 100-char limit. By the time this was taken the count was eight.
So reformatting fixes the day's report and not the cause: the next release
picks different files and the first session to notice pays again.

That is why this needs both halves. Pinning ruff exactly makes a style change
an explicit edit with a commit message behind it rather than a side effect of a
lock refresh; putting `format --check` in the gate makes the tree's agreement
with that pin an invariant instead of something a person discovers. The state
to avoid is the current one, where a formatter is configured, disagrees with the
tree, and is enforced by nothing — so anyone who runs it on a file they were
editing emits diff noise unrelated to their change. Declining to enforce it
would have to be written down somewhere a reader finds, and v2's argument that
the machine-checked tables stayed true while the prose around them drifted cuts
the other way.

This item is the one home for that defect. `the-formatter-is-in-the-gate-or-it-is-not`
and `the-gate-does-not-check-formatting` were the same finding minted again by
later sessions and are folded in here — with 03.7.1's two attempts, 04.3, and
05.3's re-take, four sessions minted it under four slugs without reading the
pool, which is
`docs/findings/loop/2026.08.07-the-pool-is-not-read-before-an-item-is-minted-into-it.md`.

Whether v3 gates on types is a real decision and not a rider on this one; it is
`nothing-in-v3-type-checks.md`.

## Worker note, 2026-08-07

Both halves landed in one commit, with the reformat in it and nothing else.

`ruff==0.16.1` in the dev group — the version `uv.lock` already resolved, so
the lock moved by one line and no environment's behaviour changed today. It is
the only exact pin in the file, and the comment there says why an `==` is right
for the formatter where a floor is right for a library.

`uv run ruff format .` rewrote eight files: `scripts/doc_index.py`,
`src/sieve/pipeline/executor.py`, `tests/integration/test_checkpoints.py`,
`test_crop_serving.py`, `test_stirred_clip.py`, `tests/unit/test_crop_binding.py`,
`test_import_contracts.py`, `tests/unit/test_tool_contract.py`. Every hunk is a
line-joining or line-splitting decision or a blank line; the one worth a
reviewer's eye is `doc_index.py`, where the formatter unaligned the trailing
comments on `DEFER_REASONS`.

The gate line in `.github/workflows/ci.yml` is now
`uv run ruff check . && uv run ruff format --check . && uv run lint-imports && uv run pytest -q`,
green as a whole: `All checks passed!`, `331 files already formatted`,
`Contracts: 6 kept, 0 broken.`, `617 passed in 12.18s`.

Its comment no longer claims the list is "character-for-character what a commit
is checked against locally". There is no local list — no noxfile, no gate
command in `README.md` or `CLAUDE.md` — so the claim had no referent, and
porting v2's nox session to give it one is not warranted by a line in a
comment. The comment now says what is true: this line is the gate and there is
no second copy of it. 00.3's `done_when` still holds the three-command form and
is left alone, `done_when` being a reviewer's to edit.

Not done here: nothing re-runs `doc_index.py`'s `--check` in the gate, and the
formatter has no opinion about `.md` or `.yml` at all, so both remain checked
by habit.
