---
title: The one VISION never-line that no contract checks gets one
priority: normal
phase: "0"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_import_contracts.py -q"
opened: 2026-08-06
---

# The one VISION never-line that no contract checks gets one

`.importlinter`'s header calls the file "the forbidden edge set of VISION.md's
component table, made checkable". Walking the table's `Never` column against the
five contracts, every import-shaped never has a contract behind it except one:
`pipeline` must never reach into `ops/`. It is legal under every contract in the
file — `core` sits below `pipeline`, so the import points downward — which is
the same hole `gui-computes-nothing` exists to close one layer up, and the
reason it exists there applies here for the same reason: reaching a tool's array
math from the executor is the second execution path
(adr/one-execution-path.md), taken from the layer that owns the first.

Either the edge gets a contract or the header comment stops claiming the set is
complete; the first is the one worth having. The entry is inert until
`src/sieve/core/ops/` exists
(`docs/findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`),
which adr/ops-admission-is-two-tools.md defers past this item, so
`uv run lint-imports` cannot go red for the new line and is not the criterion.

`done_when` is a new `tests/unit/test_import_contracts.py`, holding two things
about the entry: that `.importlinter` declares a `forbidden` contract with
`sieve.pipeline` among its sources and `sieve.core.ops` among its forbidden
modules, and that the entry fires — the finding's second probe, run as a test
rather than by hand, in a copy of the tree where `sieve/core/ops/` exists and a
`sieve.pipeline` module imports it, asserting `lint-imports` exits non-zero and
names that contract. Without the second assertion the test only reads back the
line the same commit wrote. Proving it against a copy is what lets the proof of
red land with the line instead of waiting on ops admission; the per-line,
generated version of the same idea is
`docs/todo/proof-of-red-covers-every-line-of-a-contract.md`, and this is one
line by hand, not that mechanism.
