---
title: The gate has no opinion about the workflow that runs it
priority: low
phase: 0
status: open
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
