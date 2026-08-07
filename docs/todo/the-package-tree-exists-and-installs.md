---
title: The package tree exists and installs
step: "00.1"
status: awaiting-review
gated_on: nothing
done_when: "uv sync && uv run python -c \"import sieve\""
opened: 2026-08-06
---

# The package tree exists and installs

`src/sieve/` with `core`, `tools`, `pipeline`, `decode`, `cli`, `compat` as
empty packages — `gui`, `bench`, `storage` are declared in the contracts but
get no directory until something lives there. `pyproject.toml` flips
`package = false` to a hatchling build block in the same commit, as its own
comment instructs.
