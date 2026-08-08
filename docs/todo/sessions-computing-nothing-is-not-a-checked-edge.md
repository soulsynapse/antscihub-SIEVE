---
title: The session row's "computing anything" never has no contract behind it
priority: normal
phase: "7"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_import_contracts.py -q -k session"
opened: 2026-08-08
---

# The session row's "computing anything" never has no contract behind it

`.importlinter`'s header calls the file "the forbidden edge set of VISION.md's
component table, made checkable", and the `session` row's never-cell names
three: Qt, command inversion, and computing anything. The first is `headless`,
which the file states in a comment on that very line. The second is not
import-shaped and no contract could check it — undo moving a pointer is what
`tests/unit/test_session.py` holds. The third is import-shaped and unchecked:
`sieve.session` sits above `sieve.tools` and `sieve.core` in the layers
contract, so a session module importing a tool's `run` — or `sieve.core.ops`
the day it exists — points downward and is legal under every contract in the
file. That is the same hole `gui-computes-nothing` closes one layer up and
`pipeline-computes-nothing` closes one layer down, for the same reason: a
second execution path taken from a layer that is supposed to ask for the first
(`adr/one-execution-path.md`).

The line was inert while the package was empty, which is why the Phase-0 sweep
that closed `pipeline -> core.ops`
(`todo/pipeline-reaching-into-ops-is-not-a-checked-edge.md`) left it. 07.2 gave
the package contents, and 07.3–07.9 write into it with a graph, a store and a
tool registry all one import away.

`done_when` extends `tests/unit/test_import_contracts.py`, whose existing case
is the model: read back that a `forbidden` contract names `sieve.session` among
its sources and `sieve.tools` among its forbidden modules, *and* prove the
entry fires — a copy of the tree where a `sieve.session` module imports
`sieve.tools`, asserting `lint-imports` exits non-zero and names the contract.
Whether this is a fourth contract or a widening of `gui-computes-nothing`'s
source list is the item's to decide: the two rows forbid the same modules for
the same reason, and a shared contract would put `gui` and `session` under one
name that says neither.
