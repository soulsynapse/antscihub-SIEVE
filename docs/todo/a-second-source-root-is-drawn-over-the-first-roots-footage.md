---
title: A second source root is drawn over the first root's footage
priority: high
phase: "10"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k a_second_source_root_is_not_drawn_over"
opened: 2026-08-10
---

# A second source root is drawn over the first root's footage

Split out of
[the-canvas-shows-the-result-over-the-input.md](the-canvas-shows-the-result-over-the-input.md),
whose 2026-08-10 review paragraph named it and whose criterion cannot reach it:
that item's graph has one root, so nothing there distinguishes the input layer a
root is given from the only footage in the project.

The composite reads a root's input from `FrameResult.source`, falling back to
`app._source_frame`. Both are *one* frame for the whole render, not one per root.
A graph with two source roots — which
[crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md)
made ordinary, since a checkpoint read-back is a root that never decoded the
project's footage — therefore draws the second root over a picture it has
nothing to do with, and the user is shown a blend of two unrelated clips with
nothing on the surface saying so.

The two ways out are a decision this item does not get to make on its own. The
first is the reading of that item's own paragraph 1 taken literally — a source
step shows its result alone, so the composite is refused wherever the walk
stands on a root, which costs nothing to hold and gives up the footage-root case
where the blend is a harmless no-op. The second is a per-root input, which means
the render carrying a frame per source rather than one, and is the larger change
of the two. The criterion is written to be satisfied by either: it asserts only
that the second root's under layer is not the first root's footage, which is
true of a refusal and true of a correct per-root input.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/gui -q -k a_second_source_root_is_not_drawn_over
    253 deselected in 1.14s
    exit: 5
