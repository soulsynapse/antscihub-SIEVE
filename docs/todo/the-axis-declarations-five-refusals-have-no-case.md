---
title: The axis declaration's five refusals have no case
priority: low
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit -q -k 'axis_for_no_such_field or axis_on_a_kind_that_is_not_a_band or band_with_no_axis or row_axis_that_does_not_ascend'"
opened: 2026-08-10
---

# The axis declaration's five refusals have no case

`ToolSpec.param_axes` arrived with three registration refusals — an axis naming
no such field, an axis over a parameter that is not a band, and a band with no
axis — and `RowAxis.__post_init__` with two more, fewer than two coordinates and
coordinates that do not ascend finitely. `param_surfaces`, which they are
modelled on line for line, has one test per refusal in
`tests/unit/test_tool_contract.py`; these have none. `make_spec` there
`setdefault`s an axis onto every band, so the band-with-no-axis branch is the
one the fixture guarantees can never fire in the suite that would catch it.

All five were run by hand at review and all five fire with the message they
promise, so this is regression cover and not a suspected defect. What makes it
worth a row anyway is which branch it is: registration-time refusal is the whole
of `adr/declared-means-verified.md`'s enforcement, and a refusal that no case
enters is a refusal a later edit can delete without anything going red — the
shape `four-checkpoint-writer-refusals-have-no-case.md` and
`enum-is-refused-by-nothing-at-registration.md` already record twice.

The `RowAxis` pair wants one case, not two: non-finite and non-ascending share a
message and a raise, so a single parametrised case over `(1.0,)`, `(1.0, 1.0)`,
`(2.0, 1.0)` and a `nan` is what proves the line rather than the branch above it.

Not in scope, and named so it is not folded in by accident: whether
`gui/surface_panel._fraction_of`'s cell-centre convention actually registers
with what `_paint_field` draws. That claim lands only in `paintEvent` and is
outside every oracle the tree has
([findings/loop/2026.08.09-an-items-clause-that-lands-only-in-paintevent-is-outside-every-oracle.md](../findings/loop/2026.08.09-an-items-clause-that-lands-only-in-paintevent-is-outside-every-oracle.md)),
which is a different problem from a refusal nobody entered.
