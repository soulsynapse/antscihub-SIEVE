---
title: The gate has no opinion about the workflow that runs it
priority: low
phase: 0
status: done
gated_on: nothing
done_when: "uv run ruff check . && uv run lint-imports && uv run pytest -q"
opened: 2026-08-07
---

# The gate has no opinion about the workflow that runs it

`uvx --from actionlint-py actionlint .github/workflows/ci.yml` is the only
local check that separates a valid workflow from a broken one: green on the
file as committed, red on a copy mutated at `runs-on:` and at a step's `uses:`.
00.3's review ran it by hand, which means the next edit to `ci.yml` gets
whatever the editor remembers to run.

The decision is not whether the check works but what it costs to make it
standing. On `done_when`'s line it is one gate, as 00.3 requires, and every
commit pays for a check that can only fail when `.github/` changes. Scoped to
a `paths:` entry it is cheap and it is a second list — the shape 00.3 exists
to refuse. A third reading is that it belongs to the workflow rather than the
commit, and lives as a step inside `ci.yml` itself, which catches the error one
push too late for the push that introduced it.

Whichever way it goes, the tool arrives with it: `actionlint-py` in the dev
group rather than a `uvx` line that resolves the network on every run.

## Worker note, 2026-08-07

The gate line, as a fifth command: `uv run actionlint`, with no path argument.
`actionlint-py>=1.7` is in the dev group.

`done_when` run, all three green — `All checks passed!`, `Contracts: 6 kept, 0
broken.`, `707 passed in 26.57s` after `doc_index.py` was re-run for the two
new documents. It cannot see the item's subject, the same way 00.3's could not:
it proves the gate still passes, not that the gate now holds a fifth check. The
`run:` line and the criterion have diverged twice over — the criterion is still
missing `ruff format --check` from 00.3's amendment as well as this addition —
and both are the reviewer's to fix, so both are left alone here.

The placement argument, measured rather than reasoned
(`findings/2026.08.07-actionlint-is-seven-tenths-of-a-percent-of-the-gate.md`):

The step-inside-`ci.yml` reading is not a placement that catches the error late.
It does not catch it. Both mutations 00.3 used are re-run there against the
committed file and both are red, and both also stop the job from starting — an
unknown `runs-on` label has no runner to schedule and a step with `used:`
fails validation — so a step *inside* the job is a step that never executes.
A workflow cannot lint itself. That reading is out on its own terms, not on
cost.

Between the remaining two, cost is the whole difference, and the item's framing
of it was the thing worth checking: 0.16 s against a 24.4 s gate, 0.7%, below
the run-to-run spread of the pytest term. A `paths:` entry buys that 0.7% with
a second enumeration of which checks apply to which files — the shape 00.3
exists to refuse — and it only ever narrows CI, so it does nothing for the
laptop run before the push, which is where the whole class of error is
catchable. Two seconds would have made a `paths:` entry worth its second list;
0.16 s is not near it. (Said as "entry" throughout because the natural word for
what `paths:` does is one an ADR buried, and the doc gate reads prose, not
sense — the same collision
`findings/2026.08.07-the-rename-gate-does-not-survive-borrowed-vocabulary.md`
measured for `src/`, here in a doc and worked around rather than filed again.)

No path argument, deliberately. actionlint discovers every workflow under
`.github/` from the repo root — verified with `-verbose`, which reports
"Collected 1 YAML files" here, and works with `.git` as a worktree file — so a
second workflow file is covered by existing rather than by someone remembering
to extend a list. The failure mode that buys is a silent green if discovery
ever finds nothing; the failure mode it avoids is the one this item is about.

What is left unsettled is above this item's line rather than inside it: the
rule for what earns a place on the gate line is now argued in three files and
binding in none, and this run argued it a fourth time from scratch. That is
[what-earns-a-place-on-the-gate-line.md](what-earns-a-place-on-the-gate-line.md)
and it is an ADR, minted by its own commit — not by this one, which is an
implementation.

Verified on a runner, not only locally: the pushed commit's CI run
(31236275388) is green in 36 s with the five-command line, and installs
`actionlint-py` from the lock rather than resolving anything at run time.

One thing that push did not answer, as it turns out: actionlint drops its
shellcheck and pyflakes rules when those binaries are absent, which they are
locally, and it says which rules it dropped only under `-verbose`. A green
runner therefore does not report whether it ran more rules than the laptop. Left
as the finding's open question with what would actually settle it.

## Review, 2026-08-07

Every measurement re-run and every one of them holds. Both mutations go red
against a copy of the committed file outside the tree — `label
"ubuntu-latests" is unknown [runner-label]` and `step must run script with
"run" section [syntax-check]`, exit 1 each, exit 0 on the unmutated copy — so
the argument that puts actionlint on the line rather than inside `ci.yml`
stands on what was measured. Discovery with no path argument reports "Collected
1 YAML files" from the worktree root under `-verbose`, and names shellcheck and
pyflakes as disabled for exactly the reason the finding gives. The timings
reproduce (actionlint 0.19 s beside ruff 0.16 s, ruff format 0.15 s,
lint-imports 0.40 s, pytest 24.0 s), and run 31236275388 is `success` on
`e9d1db4` in 36 s.

What the worker left, and what the criterion could not see: nothing pinned
`actionlint` to the line. That is not a general coverage complaint — it is the
one gap `tests/unit/test_gate_line.py` exists to close, because the formatter
had already fallen off this same line for two commits, and the file's docstring
says so. Closed here rather than reopened:
`test_the_gate_line_lints_the_workflow` asserts `["uv", "run", "actionlint"]`
is one of the line's `&&`-separated commands, red with the fifth command
removed and green with it back. The criterion's own divergence is 00.3's, where
character-identity is the stated content, and it is amended there.
