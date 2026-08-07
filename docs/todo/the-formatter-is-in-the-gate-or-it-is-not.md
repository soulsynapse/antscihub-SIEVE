---
title: the formatter is in the gate or it is not
status: open
priority: low
phase: "00"
gated_on: nothing
opened: 2026-08-07
---

# the formatter is in the gate or it is not

`ruff format --check .` currently reports two files it would rewrite —
`src/sieve/pipeline/executor.py:481` and `tests/unit/test_tool_contract.py:751`
— and nothing notices, because the gate runs `ruff check` and never the
formatter (`.github/workflows/ci.yml`, `noxfile.py` does not exist here). So
the repo is in the one state that costs something: a formatter is configured,
is not enforced, and disagrees with the tree, which means the next person who
runs it on a file they were editing produces a diff that has nothing to do with
their change.

Either resolution is fine and the choice is the item. Adding `ruff format
--check` to the gate makes the two files a one-commit fix and a stable
invariant thereafter. Declining it means saying so somewhere a reader will
find — line length is already `ruff check`'s through `line-length = 100`, and
the argument that v2's machine-checked tables stayed true while the prose
drifted cuts toward enforcing rather than documenting.

Noticed while landing `sieve run` (03.8), whose own files are format-clean; the
two above predate it and are unrelated to it.
