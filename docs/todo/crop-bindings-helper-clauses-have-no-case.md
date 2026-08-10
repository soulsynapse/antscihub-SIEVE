---
title: crop_binding's helper clauses have no case
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# crop_binding's helper clauses have no case

`test_crop_binding.py` writes one case per clause of `CropRecord.backs` and each
of those clauses is pinned. The four clauses `crop_binding.py` wrote itself are
not: a machine mutation sweep over 05.2 survives four semantic mutants, all in
`backing_for` and its private helpers
(`findings/2026.08.07-the-clause-per-case-rule-covers-the-predicate-and-not-the-helpers-under-it.md`).
None is a defect — the shipped code is right in every case — so this is four
rows, not a fix.

- A window *exactly* equal to the record's span reads `AT_REST`. Every existing
  row is strictly inside the span or strictly outside it, so `>` and `<` in the
  window clause survive being widened to `>=` and `<=`. This used to be "the
  twin's half", `resolve_source`'s identical clause being pinned at the boundary
  by `test_crop_serving._resolved`; `b63f43f` retired that clause with the whole
  plan-time route, so there is no twin and this row is the only pin the boundary
  will ever have.
- A near miss is anchored on the box asked about. A record cut at a *different*
  box whose file is gone must not lend its sentence to this box — today
  `_near_miss`'s region guard can be deleted and every row still passes, because
  no row has a differently-boxed record that is also stale on a `backs` clause.
- An orphan from a re-exported source is not attributed. `_orphan_for`'s
  `cut_from` guard is only ever reached beside a region that is already claimed,
  so it never decides alone. The case is a record whose parentage is stale *and*
  whose box no longer exists: `ABSENT`, not an orphan hung on a nearby box.
- Two boxes edge to edge do not overlap. `_overlaps` is strict on all four
  sides and nothing places `x + width == other.x`, which is the arrangement a
  tiled arena grid produces and the one where a `<=` would attribute an orphan
  to a neighbour that does not contain a pixel of it.

`done_when` is the two-file command 05.2 used, plus a re-run of the sweep: with
these rows in place the four mutants above should die. The sweep is a throwaway
`ast.NodeTransformer` over the module — the finding describes it — and belongs
in the item, not in the repo.

## Folded 2026-08-10: the un-serving inverse is a fifth survivor, and it is in `crop_serving.py`

Measured at the review of `33aefe3`:
[the un-serving inverse survives the whole suite](../findings/2026.08.10-the-un-serving-inverse-survives-the-whole-suite.md).
The footage field's removal forced `crop_serving._wired` to cut the edge feeding
a served crop node and `_uncut` to put it back, and the whole suite is `1296
passed` with the restoration deleted — while the forward half, narrowed back to
its pre-removal spelling, fails eleven cases. The docstring calls the
restoration "what makes the pair an edit and its undo", so this is the fifth row
of exactly the shape the four above have: shipped code that is right and that
nothing would notice the loss of.

- A served project un-served has its crop node fed by the graph's footage root.
  `test_a_served_project_can_be_cut_again` and
  `test_a_replicate_added_to_a_served_project_runs` reach `_uncut`'s parent
  lookup — reversing the walk it uses fails both — and assert nothing about
  whether the answer is wired in. The case is the restored graph's edges, or a
  run over the un-served document that would have to read the parent.

This widens the item past `crop_binding.py`, which its title still names. It
lands here rather than beside the serving item because "a clause in this
mechanism with no case" is what this item is, and a second item for a fifth row
of it would be the same item twice.
