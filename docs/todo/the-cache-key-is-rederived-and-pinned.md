---
title: The cache key is re-derived and its layout pinned
step: "03.4"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_cache_key.py -q && uv run pytest tests/unit/test_cache_key.py -q -k ancestor && uv run pytest tests/unit/test_cache_key.py -q -k rename"
opened: 2026-08-07
---

# The cache key is re-derived and its layout pinned

`pipeline/cache_key.py` re-derived against schema v1 under PLAN.md's
re-derivation clause. `tests/unit/test_cache_key.py` holds **11 cases in 3
classes**, and this item's table has 9 rows — the table maps v2's nine cases,
and four of the eleven answer to no v2 row at all. Two of those four were
amended in at review; the count read **9 cases** when the item opened.

The digest changes and that is the point of doing it as a re-derivation. v2's
`node_key` folds `backend_identity(backend)` into every node digest except
where the spec claimed `backend_agnostic`; `backend/` is dropped and Phase 1
cut the declaration, so the sixth position of `_digest("node", ...)` goes
away rather than becoming a hole. Every v3 key therefore differs from its v2
counterpart, deliberately, which is why the Phase 3 gate compares products
and never keys.

What must not change is what a key *means*: `resolved_params(node,
replicate)` is what makes the key canonical per replicate rather than per
node, the identity values are frozen (`adr/tools-not-filters.md`), and no
field recorded for the user's convenience may enter — `checkpoints`,
`outputs` and `visited` are on `Project` precisely so that turning a
checkpoint off for a cluster run cannot move a key.

The layout gets a pin test in the shape `bench/budgets.py` uses: the ordered
list of positions that enter a node key, asserted character-exact, so a later
edit that adds or reorders one is visible in a diff rather than in a cache
that silently misses.

## Three positions the body did not name

`visited` is v2's field and schema v1 has none — the convenience fields on
`Project` are `checkpoints`, `outputs` and `crops` — so the claim that sentence
makes lands on `checkpoints`, which the same sentence names and which is the
one the HPC handoff empties.

Two further v2 arguments go the way `backend_agnostic` goes, each on a decision
already taken. `source_key`'s `roi` is gone: the box is the crop node's
`region` parameter (`adr/detector-is-a-node.md`), so the geometry enters
through `resolved_params` at the node that cuts, and this module needs no
notion of a region. `source_key`'s `lowered_prefix` is gone with the producer
that would build one — `pipeline/lowering.py`, which PLAN.md does not build
until a budget is missed — for the reason `todo/the-key-walk-rejoins-the-graph.md`
gives about the same parameter on `Dag.node_keys`. What replaces v2's `luma:
bool` is `decode_format: CropFormat`, required rather than defaulted: the
document already spells the two formats as the source key spells them
(`core/pipeline_model.py`), and a caller that has not asked the graph about
chroma has not answered this either.

`upstream` is one key rather than a port-to-key mapping, and the port cases
below drop with it: an edge names no port, so `a - b` and `b - a` are not two
graphs schema v1 can write.

## The case table

9 rows, one per v2 case in `tests/unit/test_cache_key.py` — 9 test functions in
2 classes. Three verdicts, as 03.3's table used them: *survives* — same claim,
same name, only the fixture rewritten into schema v1's vocabulary; *replaced* —
the claim survives but is aimed at a different subject, and the v3 case is
named; *dropped* — the subject is gone, citing what removed it.

| v2 case | Verdict | v3 case, or what removed it |
|---|---|---|
| `TestIsolation::editing_one_branch_leaves_its_sibling_valid` | survives | same name; the fan-out is the same three nodes with no geometry on the replicate |
| `TestIsolation::a_pinned_replicate_ignores_the_default_moving_under_it` | survives | same name |
| `TestIsolation::the_crop_separates_two_otherwise_identical_replicates` | replaced | `the_region_separates_two_otherwise_identical_replicates` — same claim, different subject: the box is a per-replicate override on the crop node, so what separates the two is `resolved_params` and not `source_key` |
| `TestIsolation::locking_a_replicate_moves_no_key` | replaced | `turning_a_checkpoint_off_moves_no_key` — `Project.visited` has no schema-v1 counterpart, and the claim is about a field recorded for convenience, which is `checkpoints` |
| `TestIsolation::a_presentation_edit_moves_no_key` | survives | same name; `cost` leaves the substitutes with `CostEstimate` and `param_stereotypes` joins them, still checked against `SPEC_CHANNELS` rather than a typed list |
| `TestInputs::backend_identity_leaves_the_key_only_when_the_filter_claims_agreement` | dropped | `backend/` is gone (`adr/no-kernel-apparatus.md`) and Phase 1 cut `backend_agnostic` — this is the sixth position the item's body removes |
| `TestInputs::which_port_a_stream_arrives_on_is_part_of_the_computation` | dropped | no port to bind a key to; the sorted-pairs fold it pins has no expression until a two-input tool exists |
| `TestInputs::an_omitted_parameter_and_its_default_are_one_computation` | survives | same name |
| `TestInputs::refuses_a_key_it_cannot_stand_behind` | survives | same name; the three refusals are `cache_policy`'s three, unchanged |

Five survive, two are replaced, two are dropped, and both drops are the same
decision twice — one about the machine a node runs on, one about the wiring
that reaches it, neither expressible in v3.

## Two v3 cases with no v2 row

`a_luma_read_and_a_colour_read_of_one_file_are_two_computations` is the first
test `source_key` has ever had. v2's file keyed everything off a hand-walk and
asserted only about nodes, so neither the format position nor the decoder
identity — the two things that make the root a key rather than a constant — was
covered anywhere, and the decoder half is the one whose failure serves colour
pixels to a graph that asked for luma.

`the_positions_that_enter_a_key_are_pinned` is this item's layout pin, and it
asserts the arity refusal as well as the two tuples: `_digest` takes the
declared positions and refuses a part list that does not fill them, so the
declaration is what a position has to be added to before it can be hashed
rather than a comment beside the call.

## Two more cases with no v2 row, amended in at review

The nine that landed all pass with `node_key`'s `upstream` part replaced by
`None`, and all pass with the replicate's display name folded into that part —
both measured, in
[findings/loop/2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md](../findings/loop/2026.08.07-a-declared-layout-and-an-isolation-test-both-pass-with-the-ancestry-dropped.md).
So the module's headline claim and one of its stated absences are argued in the
docstring and asserted nowhere. Both holes are v2's too — its file has no case
for either — which is why the table has no row to move and these arrive as
additions rather than as verdicts on a v2 row.

`an_edit_to_an_ancestor_moves_every_key_below_it` is the complement of
`editing_one_branch_leaves_its_sibling_valid`, and the direction that fails
silently: a parameter edit on `a` must move `b` and `c`, because their pixels are
computed from its output. Isolation alone is satisfied by a `node_key` that
ignores its `upstream` argument.

`renaming_a_replicate_moves_no_key` pins what the layout pin cannot: two
replicates resolving to the same parameters key alike whatever they are called,
and `replicate_id` is out too (`Replicate` — "a rename must not invalidate an
entry keyed on it"). The pin says `upstream` is the second position; it cannot
say that position holds an upstream key and nothing else.

`done_when` selects both by name (`-k ancestor`, `-k rename`) because the bare
pytest command passed before either existed.
