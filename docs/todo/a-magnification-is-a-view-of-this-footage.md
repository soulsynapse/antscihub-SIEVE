---
title: A magnification is a view of this footage, and nothing drops it when the footage changes
priority: normal
phase: "10"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k a_new_picture_is_a_new_fit"
opened: 2026-08-10
---

# A magnification is a view of this footage, and nothing drops it when the footage changes

10.2 ported `gui/zoom.py` and gave `VideoCanvas` a `reset_zoom()`. It ported
neither of the two callers v2 has for it, and 10.2's own subject — a box drawn
on the magnified picture landing on the source pixels the user aimed at — is
silent on when the magnification should end, so this is not work that item left
half-done but a decision the port dropped on the floor. The state to verify
before starting: `reset_zoom` is defined in `gui/canvas.py` and called from
nowhere in `src/`.

v2 wires it in two places, and only the first is a defect here. `video_view.set_source_size`
resets the magnifier whenever the space ROIs are expressed in changes, and
`filter_tab` does the same to the composite pane on a new clip with the reason
in a comment beside it: a magnification is a view of *this* footage and does not
carry to the next one. In v3 the canvas is handed a new project's frames with
the zoom and the pan centre it held for the old one, and the clamp in
`view_rect` keeps the result legal — a rectangle covering the new fit — which is
why nothing goes red and the user is simply looking at the wrong part of a clip
they just opened.

What counts as "a new picture" is the part to settle rather than assume, and
walking is the case that decides it. Every step of one graph is the same footage
at the same aspect, and holding the magnification across a walk is what lets a
user compare two steps at the pixel they are arguing about — so the walk must
*not* reset, and only a new source may. `clear()` is the other candidate seam
and is the honest one for "the source has gone".

The second v2 caller is a question rather than a defect: `replicate_tab` wires a
Fit control in the tools panel to `reset_zoom`, so the user has an affordance
for the fit that is not "wheel out until it stops". v3 has no such control and
10.2 was not asked for chrome. Whether the canvas earns one belongs with
whatever gives the canvas its own controls (`CanvasPane` holds one slider and
its docstring says why it is a row and not a panel), not with the reset seam
above — but a reset with no user-facing way to ask for it is worth noticing
while the seam is open.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k a_new_picture_is_a_new_fit
    256 deselected in 0.70s
    exit: 5

## Folded 2026-08-10: the soloed cell is the second view state that carries

10.4 gave the canvas a solo — a cell of the block field picked out by hovering,
held as the window's view state and drawn as a marker — and it is dropped by
exactly one rule: `VideoCanvas` forgets the gesture when what it is showing stops
being a field or becomes a grid of another shape. That covers a walk onto a step
with a different block size and covers the picture going away, and it does not
cover the seam this item is about. Two projects whose block grids happen to have
the same shape leave the marker standing on a cell of footage the user has just
left, and — where the pin is on a block step — leave the trace under the canvas
drawn from it.

It is the same seam and the same argument: a magnification is a view of *this*
footage and so is a cell index, both survive a walk on purpose, and what must end
them is a new source. So whatever this item wires `reset_zoom` into is what the
solo has to be dropped at, in the same call — a second seam for the second piece
of state would be the place the two answers drift apart. `done_when` names only
the fit and does not reach the solo.
