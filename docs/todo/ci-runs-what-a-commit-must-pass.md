---
title: CI runs what a commit must pass
step: "00.3"
status: done
gated_on: nothing
done_when: "uv run ruff check . && uv run lint-imports && uv run pytest -q"
opened: 2026-08-06
---

# CI runs what a commit must pass

A GitHub Actions workflow running exactly the `done_when` line — ruff,
import-linter, pytest — so the local gate and CI are one command, not two
lists to keep in step. v2's `.github/workflows/ci.yml` is the reference for
runner setup; its nox indirection does not port.

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
