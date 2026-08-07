---
title: The committed tree fails `ruff format --check`, and ruff is unpinned
status: awaiting-review
phase: "00"
gated_on: nothing
priority: normal
done_when: "uv run pytest \"tests/unit/test_gate_line.py::test_ruff_is_pinned_to_an_exact_version\" \"tests/unit/test_gate_line.py::test_the_gate_line_runs_the_formatter\" \"tests/unit/test_gate_line.py::test_the_formatters_reach_into_docs_is_the_one_the_gate_declares\" -q"
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

## Review, 2026-08-07 — reopened

Both halves landed and the gate is green here as it was there:
`All checks passed!`, `330 files already formatted`, `Contracts: 6 kept, 0
broken.`, `617 passed in 11.43s`. The pin is exact, it is the version the lock
already held, the eight reformatted files are the formatter's output, and the
CI comment's unreferenced claim is gone. None of that is in dispute.

The last sentence of the worker note is false, and it is false about the thing
the commit added. ruff 0.16.1 formats Python code blocks inside Markdown, so
`ruff format --check .` reaches every `.md` in the tree: `docs/` alone accounts
for 219 of the 330 files the command reports, against 107 tracked `.py` files
in the whole repo. The worker's own run printed `331` — one more than mine,
which is the two folded items deleted and this decision item added — so the
number that proves it was on screen and read as a Python file count. Measured
in `findings/2026.08.07-ruff-format-check-over-the-root-formats-the-python-in-docs.md`.

Nothing is red today only because no file under `docs/` opens a fenced block
tagged as Python — zero of 219. That is the trap rather than the reprieve: the gate's
reach into `docs/` is now real, unargued and undeclared, and the first finding
that quotes a deliberately-broken snippet in a fenced Python block turns a
docs-only commit red in CI for a reason this item says cannot happen. Findings
quoting broken code is what `docs/findings/` is *for*.

What remains is one decision and its proof, and either answer is fine: bound
the formatter's target to the code (`src tests scripts`) so a document can hold
whatever a document needs to hold, or keep `.` and say in the gate comment that
Python inside a doc is Python the gate formats. The `done_when` pins whichever
is chosen rather than the choice, in `tests/unit/test_gate_line.py`:
`test_ruff_is_pinned_to_an_exact_version` reads the dev group and requires an
`==`; `test_the_gate_line_runs_the_formatter` reads `.github/workflows/ci.yml`
and requires `ruff format --check` in the `run:` line; and
`test_the_formatters_reach_into_docs_is_the_one_the_gate_declares` writes a
Markdown file holding an unformatted Python fence and asserts the gate's target
answers the way the comment beside it says it will. The third is the one with
content — this defect existed because the reach was a sentence rather than a
check, and the repo's own rule is to prefer a claim a test can check.

Not reopened for it, because the commit did not introduce it: `git add -A` is
what staged this work
(`findings/loop/2026.08.07-git-add--a-commits-the-tree-the-run-inherited-not-the-work-it-did.md`),
and it was safe only because the tree it inherited was clean. The two folded
items were deleted rather than adjudicated, which is a status call a worker does
not have; the fold itself is right and nothing was lost — `tool_base.py`'s
first sighting and the "either it joins the gate or `pyproject.toml` says which"
framing both survive above — so this is noted and not undone.

00.3's `done_when` is amended to the four-command line, which is the reviewer's
edit the worker correctly declined to make.

## Worker note, 2026-08-07 — the reach is bounded

Of the two answers the review offered, this took bounding over declaring, and
by file type rather than by directory: `[tool.ruff] extend-exclude = ["*.md"]`
in `pyproject.toml`, with the reason beside it. Narrowing the gate's target to
`src tests scripts` would bind CI and nobody else — a person who runs `uv run
ruff format .` on the file they are editing still rewrites the fenced Python in
219 documents, and diff noise unrelated to the change is the state this item
exists to end. The exclusion also covers the Markdown outside `docs/`
(`README.md`, `CLAUDE.md`, `tests/goldens/oracle_stirred/README.md`, and a
tool's `.md` beside its module when one lands), which a directory list would
have had to enumerate and keep current. The gate line is unchanged; its comment
now says its `.` is Python only and points at the config for why.

`ruff format --check .` reports 109 files where it reported 330, which is 107
tracked modules plus `pyproject.toml` plus this item's new test.

`tests/unit/test_gate_line.py` holds the three the `done_when` names. The third
pins the property and not the mechanism: it reads the gate's own target out of
`ci.yml`, runs the pinned ruff against a copy of `pyproject.toml` over one
unformatted document and one unformatted module, and requires the module
reported and the document not. Bounding by directory later answers the same
way, so the test survives changing the answer — what it refuses is the reach
becoming a sentence again. All three were shown red first: the third against
today's tree, the other two against a tree with the pin loosened to `"ruff"`
and `format --check` cut from the gate line, since they pin what `a7efe4b`
already landed.

The finding is closed with the resolution in its consequences. Its open
question is untouched and still live: `extend-exclude` names `*.md` alone, so a
later ruff that formats `.toml` or `.yml` re-opens the same trap, and the exact
pin is the only thing holding that shut.
