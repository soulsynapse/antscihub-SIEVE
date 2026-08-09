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
