---
title: The mutual tier — shared by dependency, not by agreement
status: open
opened: 2026-07-29
priority: normal
gated_on: nothing
reads: [.importlinter, src/sieve/core/shares.py, src/sieve/core/machine.py, src/sieve/core/pool_meter.py]
---

# The mutual tier — shared by dependency, not by agreement

REWORK.md R4's placement test for `core/` is agreement: would two independent
implementations have to agree on this to interoperate? `shares.py`,
`machine.py`, and `pool_meter.py` fail it — two implementations with
different worker splits produce identical results at different speeds. They
sit low because `decode/prefetch.py` and all of `gui/` both need them: a
dependency fact, not an agreement requirement.

Declare `(sieve.mutual)` parenthesized in `.importlinter` first — the
contract governs it from its first commit — then move the three modules and
update SCAFFOLD's lines. `gui/concurrency.py` stays in `gui/`: it is the
interactive session's *policy* over the readings, and policy about sharing a
machine belongs to the process sharing one (ARCHITECTURE.md, *Dividing the
machine*, last paragraph — that reasoning does not move).

Do this before, or independently of, the R6 type items — but note the types
themselves do **not** land here: `MediaDuration`/`WallDuration`/`WorkUnits`
pass the agreement test and belong in `core/types.py` permanently. The old
REWORK draft's step 3 ("split the tier before the units or they move twice")
was wrong about that, and the correction is recorded so it is not re-derived.
