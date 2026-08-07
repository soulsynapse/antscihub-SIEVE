---
title: CI runs what a commit must pass
step: "00.3"
status: awaiting-review
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
