---
title: A second source root is drawn over the first root's footage
priority: high
phase: "10"
status: done
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

## 2026-08-10 (review): closed by the refusal, and the fork was already ruled

`done_when` is `1 passed` here. It discriminates: with `ee5420c`'s two source
hunks reverted and the case as committed, the under layer is a 160×120
grayscale of the *project's* clip while the root's own result is a different
160×120 grayscale, so the assertion fails — the fixture's two files differ, which
is what its own docstring says it chose `synthetic_video` for. The parent's
criterion is `3 passed` unchanged beside it, and `tests/gui` is 265.

The fork this item said was not its to make was not made here either.
`adr/the-walked-step-owns-the-canvas.md` rules it in its own sentence — a source
step has no input, so its composite is its result alone — so the refusal is the
bound reading and the per-root input is not owed. The parent carries a dated
section saying its paragraph 3 is repealed by this.

What the criterion never reaches, and where it went: `app.input_of`'s docstring
still tells the reader `render_at` reads a root's `None` as the decoded frame,
which is the sentence this commit repealed two files over. That is
[input-ofs-docstring-still-says-a-root-is-drawn-over-the-decoded-frame.md](input-ofs-docstring-still-says-a-root-is-drawn-over-the-decoded-frame.md),
minted because no open item owns `app.py`'s prose and none would have carried
it.
