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
