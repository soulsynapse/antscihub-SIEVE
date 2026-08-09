---
title: A truncated unpinned set is pinned, and duplicates the fast class
priority: low
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_sweep.py -q -k 'the_core_count_axis_does_not_truncate_the_unpinned_set'"
opened: 2026-08-09
---

# A truncated unpinned set is pinned, and duplicates the fast class

`class_core_sets` returns one set per performance class and then the whole
allocation labelled `unpinned`, and the two are deliberately not deduplicated:
`bench/sweep.py` argues that "pinned to everything" and "not pinned at all" are
different treatments because only the second permits migration, and the sweep's
own readings bear that out — the `unpinned` row beat both pinned classes at
every worker count measured.

`cli/sweep_cmd.py` then feeds every one of those sets to `sized_core_sets`,
including `unpinned`. A truncated set is passed to `process.cpu_affinity`, so
`unpinned[:4]` is pinned, and the argument that earned the row its place is gone
the moment it is truncated. Worse, the CPUs are the same ones: `class_core_sets`
sorts the fast class first and `sized_core_sets` truncates from the front, so on
a machine whose fast class is at least as large as the requested size,
`unpinned[:N]` and `class<fast>x<M>[:N]` are the identical mask under two labels.
The 2026-08-09 sweep read them within 2% of each other at all three sizes, which
is a third of the sized rows spent re-measuring a treatment already in the table
while claiming to be a different one.

The named test is the claim, not the shape of the fix. Whether the command skips
`unpinned` when building the core-count axis, or `sized_core_sets` refuses a set
it cannot honestly relabel, is a choice between putting the knowledge in the
caller and putting it in the module — and `sized_core_sets` today knows nothing
about where its `source` came from, which is why it is not obviously the second.

Not urgent: it costs sweep time and a reader's confusion, never a wrong reading
of a cell that was actually taken.

## Two of `bench/sweep.py`'s own guards have no case either (folded 2026-08-09, review of 47bf42c)

The ported test file is faithful to v2 and two of the module's claims are
unasserted in both trees, found by a six-mutant sweep over
`src/sieve/bench/sweep.py` against `uv run pytest -q tests/unit/test_sweep.py`
(4 killed, 2 survived). They land here because the fix is cases in
`tests/unit/test_sweep.py`, which is the file this item's criterion already
adds to.

`process.cpu_affinity(original) ==> pass` SURVIVED — deleting the `finally`
that unpins the process leaves all seven cases green, including
`test_affinity_is_restored_when_the_objective_raises`, which is named for it.
Every cell in the file pins to `available_cpu_ids()`, so the mask the sweep
sets is the mask already in force and restoring is indistinguishable from not.
The test module's docstring states this as a design constraint and it is a
sound one — a suite that pinned itself to four cores would be what
`bench/sweep.py` refuses — but the property is still checkable without ever
changing a real mask, because `sweep` constructs its own `psutil.Process()`:
a seam there, or `psutil.Process` patched in the module, lets a double record
the restore. This is the more serious of the two; the guard exists because the
failure is silent and outlives the run, and nothing would notice its removal.

`return min(self.samples) ==> return max(self.samples)` SURVIVED — `Reading.best`
and `Reading.typical` are argued apart at length in the docstring and no
fixture holds two samples that differ, so `min`, `max` and `median` are
interchangeable across the whole file. `curvature` reads `best` and
`sweep_cmd` reports both, so the distinction is load-bearing in the report the
command prints. One case with unequal samples closes it.

Neither is a defect the port introduced; both are v2's, carried across intact
(`findings/loop/2026.08.07-a-verbatim-test-port-inherits-the-blind-spots-of-the-file-it-ports.md`).

## The colour core-count reading is now owed, and this fix is what makes it worth taking (folded 2026-08-09)

Folded from the run that put a `CORES_PER_WORKER` floor under `resolve_workers`
(`the-luma-cap-is-slower-than-sequential-on-a-small-allocation.md`). That floor
applies to both paths, and below 16 CPUs the colour side of it rests on the
mechanism rather than on a reading — the sweep's core-count axis was run on the
luma path only. `sieve sweep --colour --core-counts 2,4,8` is the command that
settles it, and the constant is one number either way, so this is a sweep to run
rather than a design to decide.

It lands here because running it first would spend a third of its rows on the
duplicate treatment this item exists to end: `unpinned[:N]` and the fast class's
first N are the same mask, so a colour run taken before the fix reports the same
cells twice under labels that say otherwise, and the row a reader would most want
— a genuinely unpinned small allocation — is the one it would not contain. Fixing
the axis and then reading the colour path is one ordering; the reverse throws the
reading away.

This is a measurement, not a criterion: the `done_when` above is about the axis
and does not cover the sweep, so a review may want to widen it or split the
reading out.

## Review note 2026-08-09: this item's criterion cannot witness the section above

The colour sweep folded above is a measurement, and `done_when` is a unit test
on the core-count axis that will be green whether or not the sweep is ever run.
This is a second instance of
[a folded item outgrows a criterion that cannot be widened to match](../findings/loop/2026.08.08-a-folded-item-outgrows-a-criterion-that-cannot-be-widened-to-match.md),
and the remedy that finding settled is the one to apply: the review that finds
the axis test green rotates the criterion rather than setting `done`. The
reading has no executable form — it produces a finding, not a green command —
so the rotation is to leave the item `open` with the sweep named, and it closes
when the colour core-count cells are in `docs/findings/`.

It was not split into an item of its own because the ordering argument above is
the whole reason it has a home here: run before the axis fix, a third of its
rows are the duplicate mask this item exists to end.
