---
title: A served run elides the node its file already holds
step: "05.10"
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_crop_serving.py tests/integration/test_cli_run.py -q"
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
Nothing in `src/` does it.

`tests/integration/test_crop_serving.py::_outputs` stands in for it, and not
by the mechanism above — it plans the served run as `replicate=None`, dropping
the deviation whole. The two coincide only because that replicate's single
override *is* the crop region; a replicate that also deviated a detector
threshold would lose it, so the test's stand-in does not generalise and is not
the recipe to copy. Pinning `region` on the replicate being served is.

Worth settling while this is open: "must not run that node again" and "run it
at `WHOLE_FRAME`" are not the same thing. The substitution neutralises the
node, it does not skip it, so a served run still pays a full-frame copy and a
cache entry per frame for a crop that is already cut. Whether that is the
price of keeping the graph uniform, or whether the node should be dropped from
`dag.order` for the run, is this item's call — but the two readings must not
both be in the tree, because the second changes `plan.keys` and the first
does not.

The caller is the right home for it and that is not a dodge: `resolve` is handed
a region the caller derived from the graph, so the caller already holds the node
id that region came off. What is missing is that no caller derives either yet —
`sieve run` reads the project's video for every replicate and never calls
`resolve`, which its own docstring flags as the Phase 5 gap. So this item is the
join: derive the region per replicate, resolve, elide, and run.

Shares the derivation with `the-materialize-command-derives-what-v2-was-handed.md`
— a graph with no crop node at the root, a replicate that overrides nothing, two
crop nodes and no way to choose — and this lands first, so it is the one that
puts the derivation somewhere 05.12 can call. Until then a written crop is read
by tests only, which is O3's headless creation-and-reuse loop half-closed.

After 05.9 and not before it. This is what makes `resolve` reachable from
`sieve run`, and until the coverage clause is fixed that reachability is a
crash on any graph with a window rather than a feature.
