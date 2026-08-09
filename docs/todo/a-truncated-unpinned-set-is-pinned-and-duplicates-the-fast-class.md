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
