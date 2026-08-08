---
title: Crop serving and checkpoint read-back become source tools
status: deferred
deferred_for: subject
gated_on: the-first-source-tool-moves-the-three-single-root-assumptions.md landing, because there is no source tool to migrate onto until it does
priority: high
phase: "05"
done_when: 'uv run pytest tests/integration/test_crop_serving.py -k "the_served_graph_holds_no_crop_node or a_pre_cropped_folder_needs_no_crop_record" -q'
opened: 2026-08-07
---

# Crop serving and checkpoint read-back become source tools

[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
now says the two places a file already stands where a node stood are instances
of the source-tool mechanism rather than paths beside it. This is that
migration. Nothing here re-decides it; what is owed is the tree agreeing with
the ADR.

Two things move and a third dissolves. `resolve_source.resolve` currently
answers "which file does this run open, in whose frame numbering" by matching a
`CropRecord` against a region the caller derived from the graph — that match
survives, but its product becomes a document edit offered to whoever holds the
project, not a file handed to a run already planned. The checkpoint side has no
reader yet, which is the cheap half: it is written as a source tool the first
time rather than migrated into one. And
[a-served-run-elides-the-node-its-file-already-holds.md](a-served-run-elides-the-node-its-file-already-holds.md)
is the third — it is open, it is asked to settle whether a served run
neutralises the crop node at `WHOLE_FRAME` or drops it from `dag.order`, and
under the ADR neither happens because the executed graph does not contain the
node. **Those two items must not both land.** Whichever runs second is
re-deciding, so if 05.10 lands first this item is the one that unwinds it, and
if this one lands first 05.10 loses its subject and should be closed rather than
worked.

What must hold after, and is what the criterion is for: a run served by a
written crop executes a graph whose root is a source tool over that file and
which holds no crop node at all, and a folder of pre-cropped videos wires in
with no `CropRecord` anywhere — same mechanism, no crop node to hang one on,
which is the case that forced the ADR. Cache keys are the guard on both: the
child-source model already roots a served run off the artifact's own identity
with no region in the key, so Phase 5's second gate should pass unchanged across
this migration, and it failing is the signal that the two routes were not
producing the same keys after all.

Where the clause work goes is open and is this item's call.
`crop_binding.py`'s four states are facts about records and stay facts, but a
state that used to mean "this run will be served" now means "this edit is
offerable", and the reader that displays them is downstream of a decision
somebody makes rather than of one the planner already made.
