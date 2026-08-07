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
empty packages. `pyproject.toml` flips `package = false` to a hatchling build
block in the same commit, as its own comment instructs.

Revised 2026-08-06 (Kendrick): `gui`, `bench`, and `storage` get directories
too, reversing this item's original "no directory until something lives
there" — because an `__init__.py` is no longer empty: it carries the one-line
ownership statement SCAFFOLD derives, and for `gui` that line is the
never-list itself.
