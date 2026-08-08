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
which is the case that forced the ADR.

Cache keys are not one guard over both halves, and the ADR now says which is
which. The crop half moves no key *provided the crop node is dropped rather than
neutralised*: `dag.node_keys` folds `source_key(<file>, decode_format)` into
every root and schema v1 puts no region in it, so a root reading the written crop
already folds the string a source tool over that file folds — but a node left in
at `WHOLE_FRAME` stands between them and moves everything below. Assert that
equality directly, over the two key dicts; Phase 5's second gate does not cover
it, because it runs one project twice with only its checkpoint list changed and
never derives a key both ways.

The checkpoint half does move keys, off the checkpointed node's key and onto the
written file's identity, and that is owed here rather than discovered later: this
item re-states Phase 5's second gate in `PLAN.md` so it says what a read-back
that is a document edit can actually satisfy. Re-stating a gate is a change to
the plan, so it is proposed to Kendrick and not written past him.

**Only one front end serves a crop, and this is what makes that stop mattering.**
08.2 landed the plan-time route in `cli/run_cmd.py` and nowhere else, so a
preview session and a GUI render worker still decode the parent and re-cut a box
that is already on disk — which `resolve_source.py`'s opening paragraph has
claimed all three call, since before any of them did. Under the wired form there
is no call to add: the substitution is a mutation the project holds, so a front
end that reads the document is served without knowing artifacts exist. Unwinding
`_route` and its two-pass shape is this item's work either way; what the gap
says is that the alternative — teaching two more front ends the same plan-time
route — is work with the same known expiry and should not be done.

Where the clause work goes is open and is this item's call.
`crop_binding.py`'s four states are facts about records and stay facts, but a
state that used to mean "this run will be served" now means "this edit is
offerable", and the reader that displays them is downstream of a decision
somebody makes rather than of one the planner already made.
