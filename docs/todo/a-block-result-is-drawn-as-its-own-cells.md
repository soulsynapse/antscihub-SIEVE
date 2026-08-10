---
title: A block result is drawn as its own cells over its input
step: "10.3"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k block_field"
opened: 2026-08-09
---

# A block result is drawn as its own cells over its input

Standing on `block_signal` shows its values as a coloured field of cells over
the footage they were measured from, instead of a greyscale image of a
`(ny, nx)` array stretched to fill the viewport. The painter dispatches on
`ElementKind` (`adr/an-outputs-kind-is-the-picture-it-makes.md`), with an entry
for `PIXEL` and one for `BLOCK` and none for `FRAME`, whose absence is its
answer.

It lives in a new `gui/emission_paint.py` rather than in `canvas.py`, whose
docstring is a promise that it paints one image and decides nothing, and rather
than in `kind_editors.py`, whose shape is a widget that emits an intent where
an overlay emits none. The canvas is *handed* the kind — `app._elements`
already folds it on `_reread_graph` — and never looks one up, which is what
keeps the registry out of a widget and the `gui-computes-nothing` list empty.

v2's `_paint_heat` ports body-verbatim and its shape is load-bearing rather
than incidental. Its inputs are `(ny, nx)`, one float per cell, a scale and
integer edges; nothing in it names `detect` and nothing in it could — it looked
tool-shaped in v2 only because `filter_tab` handed it detect's band power, and
here it is handed the walked node's own output. Building the layer as one ARGB
image by `np.repeat` over the same `grid_edges` the hit test reads is what
keeps colour and cell boundary from landing on different pixels, and v2
measured the obvious per-cell form at the reference block count as a repaint
slower than the frame it draws over. Porting the idea and not the shape gets
that number back.

One reconciliation has to be written down rather than landed silently.
`canvas.image_of` stretches between each frame's own extremes and argues why —
a picture has no axis, and a fixed range blacks every tool whose units are not
already 0..1. A cell's colour has the opposite requirement: it must mean the
same thing at every playhead position, or the field says nothing about which
block is loud. The answer is per kind, which is convenient rather than
accidental — `PIXEL` keeps `image_of`, `BLOCK` takes a window-fixed range off
`graph_panel.value_range` — and the module should say so where a reader meets
the second rule.

What the field costs is charged to `scrub_to_repaint`, since on a drag
`_paint_viewport` runs with `render=False` and the overlay still paints at
pointer speed. Measure it at the reference block count and not at whatever a
fixture happens to produce; that is an attribution, not a new ceiling, and a
new budget row here would be `scrub_to_repaint`'s own subject asked at a second
call site.

The claims this lands are mostly painted ones — the colouring and the cell
boundaries have no geometric referent to assert in place of the pixels — which
is the shape `the-source-badge-is-painted-by-nothing.md` exists for. Its
prescribed fixture is the one to reuse: a `grab()` of the canvas over one field
differing from the same canvas over another.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k block_field
    181 deselected in 0.7s
    exit: 5
