---
title: The canvas shows the walked step's result over its input
step: "10.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'result_over_input or off_one_render'"
opened: 2026-08-09
---

# The canvas shows the walked step's result over its input

`adr/the-walked-step-owns-the-canvas.md` says the picture is the referent's
composite and the tree draws one image. When this is done, standing on a step
shows that step's result blended over the step's input, at an opacity the user
holds; a source step shows its result alone; the output card shows the last
real step's result; and a step whose result is no picture shows its input,
which is the climb `app.frame_bearing` already makes.

The thing to get right is that this is **one render**, not two. `FrameResult`
carries every node's output for the frame — its docstring says the GUI is why —
so the input is the parent entry of the same result, and what `render_at` does
today is index for one node and drop the other. A second `render_frame` for the
input would be a second answer to `slider_to_preview` and would not be
attributable to either half. The criterion names that as its own case rather
than leaving it as a property of the implementation, because the composite is
correct either way and only one of the two is affordable.

Two edges are the work's to hold rather than to discover. The upstream id comes
off `pipeline.edges`, and schema v1 refuses two edges into one node, so there is
never a parent to choose between — the same fact `walk.py` and
`pinned.element_kinds` already stand on. And at a root the input is
`result.source`, which is `None` on a warm re-render where nothing decoded;
`app._source_frame` is the transport's proxy at that index and is the answer,
which is v2's semantics rather than a fallback invented here.

`viewport_node` must keep returning `None` for a region-cutting root. The crop
editor draws its box over the source and its coordinate space depends on that;
a composite that renders the walked step unconditionally breaks the editor and
pays a render nothing asked for.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k 'result_over_input or off_one_render'
    181 deselected in 0.7s
    exit: 5

## 2026-08-10 (review): the criterion is green with the input layer never drawn

Reopened rather than closed. The implementation that landed in `709d6b0` is
right — `render_at` returns both layers off one render, `input_of` reads the
single upstream edge, the root falls back to the transport's proxy, and
`viewport_node` is untouched, so the region editor still gets the source alone.
What did not land is a criterion that can tell any of that from its absence for
the claim this item is named for.

Delete one line from `VideoCanvas.paintEvent` — `painter.drawImage(box,
self._under)`, leaving the layer held, exposed on `.under`, and never
painted — and `done_when` is still `2 passed`. The three grabs the case
compares sweep the *result*'s alpha, so at opacity 0.0 the grab is the empty
letterbox, which differs from the other two exactly as a real input layer
would. The case's own docstring diagnoses the field-assertion version of this
hole correctly and the grab version has it too. Mechanism and the mutant's
exit in
[findings/loop/2026.08.10-three-grabs-that-all-differ-are-green-with-the-under-layer-never-painted.md](../findings/loop/2026.08.10-three-grabs-that-all-differ-are-green-with-the-under-layer-never-painted.md).

What closes it is one grab pinned to a picture rather than to another grab: at
opacity 0.0 the canvas must equal the canvas handed the input image as its only
frame, which is false for a background and false for a layer nobody drew. The
`off_one_render` half needs nothing — it counts `render_frame` calls and asserts
`under is not None`, and both move under the mutation that matters to it.

**The two sentences of this item that disagree, and the reading that stands.**
Paragraph 1 says a source step shows its result alone; paragraph 3 says a root's
input is `result.source`. The work run read them as consistent — at a footage
root the decoded frame *is* the root's own output, so the composite is a visual
no-op — and implemented paragraph 3. That reading stands and is written here
rather than left in the run log. What it does not cover, and what the next run
on this item owns: `FrameResult.source` is *one* frame for the whole render, so
in a graph with more than one source root every root gets the same input layer,
and a checkpoint-read root (`crop-serving-and-checkpoint-read-back-become-source-tools.md`,
done) would be drawn over footage it has nothing to do with. Either the composite
is refused at a source root — which is paragraph 1 read literally — or the root's
input is read from something that distinguishes the roots. Nothing exercises
either today.

**The output-card clause is struck from this item.** "The output card shows the
last real step's result" has no subject in the tree: `_order` is
`walk.node_order(pipeline)` and the output card is a `chain_stack.Outputs` built
from `kept_products`, not a `Node`, so the walk cannot stand on it and
`_paint_viewport` can never be about one. The work run named this and wrote no
code for it, correctly. It is folded into
[the-track-is-three-positions-and-the-fourth-is-a-steps-form.md](the-track-is-three-positions-and-the-fourth-is-a-steps-form.md),
which already owns "the walk stands only where a node is" and the two ways out
of it. It comes back here only if that item gives the walk a place to stand.
