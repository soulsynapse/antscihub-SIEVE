---
title: The gesture's replicate address is carried by three lines no case reads
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k binds_its_overlays_at_the_selected_region"
opened: 2026-08-09
---

# The gesture's replicate address is carried by three lines no case reads

09.9 gave `SetParam` a replicate address on all three of the surfaces that
write it, and two of the three are pinned: `ParamForm`'s address dies under
mutation from the card (`test_region_verbs.py`), and `RegionEditor` honours an
id it is *handed* (`test_kind_editors.py`). What nothing reads is the path
between the window and the overlay — which is the surface the item's own body
named the symptom on, "a box dragged on the canvas moves both".

Three lines, all survivors against the whole of `tests/gui` (review of
`868692f`, `scripts/mutation_sweep.py`):

    replicate_id = self.selected_replicate ==> replicate_id = None            (gui/app.py)
    RegionEditor(..., replicate_id=replicate_id) ==> RegionEditor(...)        (gui/kind_editors.py)
    SpanEditor(..., replicate_id=replicate_id) ==> SpanEditor(...)            (gui/kind_editors.py)

The first also drops the `params_for(node_id, replicate_id)` the overlay opens
on, so the mutant is the whole pre-09.9 behaviour: every drag on the canvas and
every handle on the band writes the baseline while the fan stands on a region,
and the picture on screen is right up until the user clicks to another square.

One case kills all three, because they are one path: a window with a decoded
frame, standing on the second of two regions, dragged on the canvas, asserted
to have pinned that replicate's override and left its sibling's empty. The
fixture is not new — `tests/gui/test_app.py`'s second case decodes real footage
and waits for a settled refill, which is what `region_extent` being non-`None`
needs. The band's handle is the same claim on the other surface and the same
window can carry it.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k binds_its_overlays_at_the_selected_region
    216 deselected in 0.68s
    exit: 5

## Folded 2026-08-10 at review: the band's handle is a fourth line, and its own value is unasserted

`BandEditor` landed with the surface panels and takes `replicate_id` the way
the other two do, so the survivor list above is four lines rather than three:
`BandEditor(panel, *bound, replicate_id=replicate_id)` in
`kind_editors._on_the_surface` is the same drop on the third surface. The
sentence above about the band's handle being "the same claim on the other
surface" was written before there was a handle; there is one now, and the case
this item asks for is the one that reads it.

The same case is owed a second assertion that has nothing to do with the
address. `test_band_surface.test_a_dragged_band_surface_handle_enters_as_a_set_param`
drags the low edge to 0.75 on a fixed 0..1 axis where the high edge is 0.75, so
the value it commits is exactly the value the stop-at-the-other clamp would
commit for any drag at all: with `_dragged_to`'s `START` branch replaced by
`return (high, high)`, all nine cases in `tests/gui/test_band_surface.py` pass.
The criterion as a whole still kills it — `test_band_surface_budget.py`'s
distinct-band assertion goes red — so the claim is covered, but only by a
window-driving benchmark, and the unit case that names the claim cannot see it.
A drag to any value between the edges separates them. The shape is
[the fixture's convenient value is the claim's own boundary](../findings/loop/2026.08.08-a-per-subject-revert-is-green-when-the-two-expressions-agree-on-every-fixture.md).
