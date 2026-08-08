---
title: The session layer holds the project and its two stacks
step: "07.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_session.py -q -k 'undo_restores_the_prior_whole_value or a_reopened_project_round_trips' && uv run pytest tests/unit/test_import_contracts.py -q -k session"
opened: 2026-08-08
---

# The session layer holds the project and its two stacks

The Qt-free half of the skeleton lands first because everything else in the
phase writes through it. `session/` is a new top-level package holding the open
project as a schema-v1 value and undo/redo as two stacks of whole immutable
pipeline values — moving a pointer through values, never inverting a command,
with prefix reuse falling out of the executor's cache and no history-aware code
(`adr/gui-base-is-the-v25-spike.md`). The spike's `session/` is the seed and
its tests are the spec, under the re-derivation table rule from PLAN.md's
porting discipline: the spike's value types are not schema v1, so every spike
case is a row that survives, is replaced by a named v3 case, or is dropped
citing the decision that removed its subject.

The package is new to the tree, so its admission is part of the item: a layers
row below `sieve.gui` in `.importlinter`, membership in the `headless`
contract with the proof of red that a new contract line is owed
(`proof-of-red-covers-every-line-of-a-contract.md`), a component-table row in
VISION.md recording what ADR-14 already adopted, and the `__init__.py`
ownership line the table's bold spans demand. Owns the document and its
history; never Qt, never a computation — the GUI renders what this holds, the
pipeline computes what this asks for.
