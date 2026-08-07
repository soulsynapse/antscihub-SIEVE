---
title: A served run elides the node its file already holds
priority: high
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# A served run elides the node its file already holds

`resolve_source.resolve` landed with 05.2 and answers which file a run opens and
in whose frame numbering. It deliberately does not answer the third thing a
served run needs: the artifact *is* the crop node's output, so a run handed one
must not run that node again, or it cuts a box out of a box.

v2 had no gap here because a v2 region was executor machinery — a plan carried
an `roi` and `pre_cropped` suppressed it. Under `adr/detector-is-a-node.md` the
box is a crop node's `region` parameter, so there is no plan field to suppress
and the substitution has to happen in the graph: the crop node runs at
`tools/crop.WHOLE_FRAME`, the identity crop, for the replicate being served.
`tests/integration/test_crop_serving.py::_outputs` performs exactly that
substitution by hand and says so; nothing in `src/` does.

The caller is the right home for it and that is not a dodge: `resolve` is handed
a region the caller derived from the graph, so the caller already holds the node
id that region came off. What is missing is that no caller derives either yet —
`sieve run` reads the project's video for every replicate and never calls
`resolve`, which its own docstring flags as the Phase 5 gap. So this item is the
join: derive the region per replicate, resolve, elide, and run.

Shares the derivation with `the-materialize-command-derives-what-v2-was-handed.md`
— a graph with no crop node at the root, a replicate that overrides nothing, two
crop nodes and no way to choose — and whichever lands first should put it
somewhere the other can call. Until then a written crop is read by tests only,
which is O3's headless creation-and-reuse loop half-closed.
