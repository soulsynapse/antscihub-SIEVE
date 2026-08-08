---
title: CI runs what a commit must pass
step: "00.3"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_gate_line.py -q && uv run actionlint"
opened: 2026-08-06
---

# CI runs what a commit must pass

A GitHub Actions workflow whose gate step is the checks a commit must pass, so
the line a contributor runs before pushing and the line CI runs are the same
characters. The rule that argued for is settled at
[ADR 19](../adr/the-gate-is-one-line.md), and this item's `done_when` was the
second copy that produced its evidence. v2's `.github/workflows/ci.yml` is the
reference for runner setup; its nox indirection does not port.

## Worker note, 2026-08-06

`done_when` run locally, all three green:

    All checks passed!
    Contracts: 5 kept, 0 broken.
    38 passed in 0.34s

The criterion cannot see the thing the item is about. It runs the gate; it
does not run the workflow, so a YAML error, a bad action pin, or a
`uv sync --locked` that only fails on a clean runner all pass it. What was
checked instead: the file parses as YAML under pyyaml, and the `run:` line is
character-identical to `done_when`. First push to `v3` is the real proof —
until then this is unverified in the way the loop is worst at detecting.

Two placements a reviewer should confirm rather than inherit:

- Triggers are `pull_request`, push to `v3`, and `workflow_dispatch`. `main`
  is deliberately absent: it is v2's branch in this same repository and a
  workflow runs from the tree it was pushed with, so a `main` entry here would
  never fire this file.
- The action SHAs are v2's pins (checkout v7, setup-uv v9.0.0) and uv is
  pinned to 0.11.32 as there. Python comes from `.python-version` rather than
  a second copy in the workflow.

## Review, 2026-08-07

Both placements stand, and the criterion's blind spot is smaller than the
worker had the means to show.

The triggers are right for the reason given. `push` runs the workflows in the
tree that was pushed, so a `main` entry in this file would only ever fire v2's;
`pull_request` runs from the merge ref, so a v3→main PR does fire this one.

The pins are now checked rather than inherited: `actions/checkout`'s `v7` tag
resolves to `3d3c42e5…` and `astral-sh/setup-uv`'s `v9.0.0` to `c771a70e…`,
both read live from the API, both the current major. Dropping setup-uv's
`python-version` costs nothing — with no interpreter installed, `uv sync`
provisions the one `.python-version` names.

The gap the worker named is narrowed, not by argument but by a check it did
not have: `actionlint` reads the file against GitHub's own workflow schema and
passes, and a copy mutated in two places (`ubuntu-latests`, `uses:` spelled
`used:`) fails on both — so the green separates a valid workflow from a broken
one, which is the thing `done_when` cannot do. `uv lock --check` resolves,
which is the failure `uv sync --locked` would raise on a clean runner.

What is left is only what a runner can answer. This branch has never been
pushed — `origin/v3` is 40 commits behind and carries no `.github/` — so the
first push is still the proof, and a push is not a reviewer's to make. Done on
that basis. Whether the gate should hold `actionlint` permanently is
`the-gate-has-no-opinion-about-the-workflow.md`, and why nothing surfaced this
item for four runs is `findings/loop/2026.08.07-awaiting-review-leaves-the-selection-rule-and-never-returns.md`.

## Amended at review, 2026-08-07

`done_when` gains `uv run ruff format --check .` as its second command, because
`a7efe4b` put it in the workflow. The item's whole content is that one line and
the `run:` line are character-identical, so a commit that moves one and not the
other leaves the criterion passing over a workflow it no longer describes —
which is what happened here for one commit. Re-run at that commit, all four
green. The amendment is the reviewer's because a criterion is; the worker saw
the divergence and correctly left it alone.

## Amended again at review, 2026-08-07

`uv run actionlint` joins as the fifth command, for the same reason and after
the same divergence: `e9d1db4` put it in the workflow
(`the-gate-has-no-opinion-about-the-workflow.md`) and left this line at four.
Re-run at that state, all five green — `All checks passed!`, `113 files already
formatted`, `Contracts: 6 kept, 0 broken.`, `708 passed in 24.32s`, actionlint
silent at exit 0. Twice now the divergence has lasted exactly one commit and
been repaired by the review that followed, which is a working arrangement but
not a checked one: nothing compares this line to the `run:` line, so the two
agree only because a reviewer noticed. The check that would close that is
`what-earns-a-place-on-the-gate-line.md`'s neighbour rather than its content,
and it is not minted here — a third occurrence is the evidence that would
justify it.

## The copy is struck, 2026-08-07

Amended from `the-gate-line-has-a-live-second-copy-adr-19-forbids.md`'s work
run, which exists because ADR 19 named this `done_when` a live copy and did not
say what became of it. `done_when` now names the check that reads the gate line
off `ci.yml` — `tests/unit/test_gate_line.py`, which is where the claims about
that step live — and
`actionlint`, which is the one command that separates a valid workflow from a
broken one and so is the part of the old line this item's content actually
turned on. Nothing here enumerates the gate any more, which is what ADR 19 asks
for and what the third drift, in the paragraph above the worker note, showed
the enumeration costs even in prose.

The two amendments above stand as the record of what the copy did. What they
should not be read as is a standing requirement to bring this line back into
step: there is no line here to bring.
