---
title: The session layer holds the project and its two stacks
step: "07.2"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_session.py -q -k 'undo_restores_the_prior_whole_value or a_reopened_project_round_trips'"
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

The package's admission is already whole — the VISION.md row, the ownership
line on a declared-but-empty package (the Phase-0 pattern), the layers row
below `sieve.gui`, and `headless` membership, whose reds
`tests/unit/test_contract_lines_go_red.py` generates from the config — so
this item adds only contents. The row's never-cell is the standard: never Qt,
never a computation — the GUI renders what this holds, the pipeline computes
what this asks for.
