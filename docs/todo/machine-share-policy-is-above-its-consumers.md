---
title: Machine-share policy sits above its consumers
status: open
opened: 2026-07-28

gated_on: >
  nothing structurally

reads:
  - src/sieve/gui/concurrency.py
  - src/sieve/core/machine.py
  - src/sieve/decode/quiet.py
  - docs/ARCHITECTURE.md
---

# Machine-share policy sits above its consumers

Rule 5 names `gui/concurrency.py` as the one declaration of how a session
divides the machine — every path that can take more than one core or a bounded
slab of memory declares its share there. The file is at the top layer, and most
of what it governs is not.

Three symptoms, all already in the tree:

- `decode/quiet.py` and `bench/retention_trace.py` refer to it **in prose**,
  because they cannot import it.
- `chain_model.recompute` takes `workers` as a required argument with no
  default, and its docstring explains that the default had to be deleted
  because the GUI inherited `ALL_CORES` by omission and ran a Morlet transform
  on the GUI thread beside two decode pools. The fix was correct; the reason it
  was needed is that the policy home is unreachable from where the policy
  applies.
- A headless caller "passes `ALL_CORES` and says so" — that is the docstring's
  words — which means the CLI's share of the machine is declared at each call
  site rather than in the one table.

**The move.** `core/machine.py` already reads the allocation (cgroup, then
scheduler, then physical) and is below everything. The share constants
(`PLAYER_WORKERS`, `PREVIEW_WORKERS`, `DETECTOR_WORKERS`, `WorkerSplit`,
`MemoryShare` and the declared slabs) belong beside it — either in
`core/machine.py` or a `core/shares.py` next to it. What stays in
`gui/concurrency.py` is the GUI session's *slice*: which pools an interactive
session runs and how they add up.

**The thing to not get wrong.** `SENSED`/`WITHOUT_SENSOR` and the ledger
producers (docs/completed-todo/2026.07.28-ledger-producers.md) currently live
against this table, and rule 4's "a ceiling nothing publishes is a number, not a
budget" applies to whatever is left holding them. Splitting the table without
deciding which half the sensor rows follow would produce two tables and one
honest gap in neither. Decide that first; it is the only real design question
in the item.

**Check afterwards** that ARCHITECTURE.md's rule 5 text names the new home, and
that the two prose references in `decode/quiet.py` and `bench/retention_trace.py`
become imports if the move makes them possible — an import is the version of
that reference the gate can check.
