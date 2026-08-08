---
title: The two VISION never-lines no contract checks get one each
priority: normal
phase: "7"
status: done
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

## `decode` has the same hole, and it is not inert (2026-08-08, review of 07.2)

Walking the whole `Never` column rather than the `session` row found a second
unchecked import-shaped never, so this item is the two of them:
`decode` must never know "what a tool or a schema is". The tool half is free —
`sieve.tools` sits above `sieve.decode`, so the layers contract already refuses
it. The schema half is not: `sieve.core` is the bottom layer, so
`sieve.decode` importing `sieve.core.pipeline_model` points downward and is
legal under all six contracts. `decode/` today imports `sieve.core.types` only,
which is the dimensioned-types half the row grants it, so the edge is open and
unused rather than crossed.

It differs from the `session` line in the way that matters for ordering: the
module it names exists today, so a contract added for it can go red against the
real tree instead of against a copy
(`findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`), and
nothing has to happen first. Both are one edit to `.importlinter` and one case
in `tests/unit/test_import_contracts.py`, which is why they are one item —
whichever shape the `session` question above settles on, `decode` takes the
same shape with `sieve.core.pipeline_model` as its forbidden module.

The count behind both: `docs/findings/2026.08.08-vision-never-column-has-two-import-shaped-lines-no-contract-checks.md`.

## The title's "two" is the walk's count, not the file's (2026-08-08, review of 44608be)

Read as a closed count it is already wrong, which is what the title invites. It
is two *import-shaped nevers in VISION's `Never` column that no contract
checked* — the walk this item came from ran table-to-config only. Walking the
other way at 44608be found three `opencv-containment` sources with no cv2 clause
in their row, and one package the file refuses nothing codec-shaped to at all;
`todo/the-cv2-refusal-skips-the-executor.md` holds that and nothing here needs
reopening for it.
