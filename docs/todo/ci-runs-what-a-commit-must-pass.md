---
title: CI runs what a commit must pass
step: "00.3"
status: open
gated_on: nothing
done_when: "uv run ruff check . && uv run lint-imports && uv run pytest -q"
opened: 2026-08-06
---

# CI runs what a commit must pass

A GitHub Actions workflow running exactly the `done_when` line — ruff,
import-linter, pytest — so the local gate and CI are one command, not two
lists to keep in step. v2's `.github/workflows/ci.yml` is the reference for
runner setup; its nox indirection does not port.
