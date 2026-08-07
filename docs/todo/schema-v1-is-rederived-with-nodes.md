---
title: Schema v1 is re-derived with nodes
step: "02.1"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_replicates.py -q"
opened: 2026-08-06
---

# Schema v1 is re-derived with nodes

`core/pipeline_model.py` re-derived as schema v1: crop, span, and the
detector are graph nodes natively (`adr/detector-is-a-node.md`). Kept
verbatim in spirit: `extra=forbid`, registry-blind, no measurements in the
artifact, checkpoints and outputs on `Project` not `Node`. No v2 field name
is spelled anywhere (`adr/v2-does-not-import.md`) — schema v1 is written as
if v2 never existed.

The replicate is part of this module rather than beside it: v2 split
`core/replicates.py` out because the model was already 1,273 lines, and
`adr/core-membership-is-closed.md` admits `pipeline_model.py` and not a
second child, so keeping the split would buy an ADR revision for nothing.

Under PLAN.md's re-derivation clause: v2's `test_pipeline_model.py` holds
**25 cases in 8 classes** and `test_replicates.py` **14 cases**, and this
item's table has 39 rows. `tests/property/test_replicates.py` is not in the
criterion — its three cases need `hypothesis`, which no v3 component has
asked for, and adding a dependency is a decision this item does not carry.

What the fields must still be able to say, because Phase 5 builds on them:
`checkpoints` (node ids whose output is written), `outputs` (the sink
records), and the crop record with its `backs` matching — associated with the
box it was cut from by geometry and parentage, never by name, so a rename
survives and a box that moved correctly stops matching. All three live on
`Project` because none of them may reach a cache key: turning a checkpoint
off for a cluster run must not change what a result is.

## The case table

39 rows, one per v2 case. Three verdicts: *survives* — same claim, same name,
only the fixture rewritten into schema v1's vocabulary; *replaced* — the claim
survives but is aimed at a different subject, and the v3 case is named;
*dropped* — the subject is gone, citing what removed it.

Two rules do most of the dropping, and neither is this item's decision.
PLAN.md's porting discipline refuses a v2 declaration the item's cut list does
not name and no v3 machinery consumes (`adr/declared-means-verified.md`) —
that is `equivalence_groups`, `ReplicateSet` and `Project.visited`, all three
of which have their first consumer in Phase 7. And `core/tool_base.py` cut the
input-port protocol until the first two-input tool, so an edge has no `port`
and a node has one input.

### `test_pipeline_model.py` — 25 cases in 8 classes

| v2 case | Verdict | v3 case, or what removed it |
|---|---|---|
| `TestRoundTrip::yaml_round_trip_preserves_the_document` | survives | same name |
| `TestRoundTrip::saving_twice_writes_identical_bytes` | survives | same name |
| `TestRoundTrip::relocating_rebases_every_stored_path` | survives | same name; the crop record's path joins the source and the sinks |
| `TestIndependenceFromTheRegistry::a_project_naming_an_unknown_filter_still_loads` | survives | `a_project_naming_an_unknown_tool_still_loads` (`adr/tools-not-filters.md`) |
| `TestIndependenceFromTheRegistry::a_filter_id_that_cannot_key_a_cache_is_refused` | survives | `a_tool_id_that_cannot_key_a_cache_is_refused` |
| `TestPurity::gui_state_cannot_be_stashed_in_the_artifact` | survives | `front_end_state_cannot_be_stashed_in_the_document` |
| `TestPurity::node_carries_identity_and_nothing_else` | survives | same name; the pinned set is `{node_id, tool_id, version, params}` |
| `TestPurity::a_document_from_a_newer_build_is_refused` | survives | same name |
| `TestPorts::a_version_1_document_loads_with_every_edge_on_the_default_port` | dropped | v2's schema-1→2 migration pin. Schema v1 is the floor and `upgrade.py` is on PLAN.md's dropped list, so there is no older document to load |
| `TestPorts::two_edges_may_not_feed_one_port` | replaced | `TestReferentialIntegrity::two_edges_may_not_feed_one_node` — with one input per node the check is stronger, not weaker |
| `TestPorts::one_upstream_may_feed_two_ports_of_one_downstream` | dropped | not expressible without ports; returns with the first two-input tool, which is when the document learns which input an edge feeds |
| `TestPorts::a_port_that_cannot_survive_yaml_and_shells_is_refused` | dropped | no `port` field to spell |
| `TestReferentialIntegrity::an_edge_naming_no_node_is_refused` | survives | same name |
| `TestReferentialIntegrity::replacing_the_graph_catches_stale_checkpoints_and_sinks` | survives | same name |
| `TestPerReplicateDeviation::untouched_replicates_follow_the_newest_edit` | survives | same name |
| `TestPerReplicateDeviation::a_pinned_parameter_does_not_freeze_its_siblings` | survives | same name |
| `TestPerReplicateDeviation::resetting_returns_a_replicate_to_the_default` | survives | same name |
| `TestPerReplicateDeviation::an_override_naming_no_node_is_refused` | survives | moved to `TestReferentialIntegrity`, where the other staleness checks are |
| `TestEquivalenceGroups::a_deviating_replicate_renumbers_every_group_below_it` | dropped | `equivalence_groups` is not carried — see below |
| `TestEquivalenceGroups::a_deviation_anywhere_in_the_graph_splits_a_group` | dropped | same |
| `TestEquivalenceGroups::geometry_and_naming_are_not_what_makes_a_group` | dropped | same, and its claim is contradicted outright by `adr/detector-is-a-node.md` — see below |
| `TestConventions::the_project_file_sits_beside_its_video` | survives | same name |
| `TestConventions::a_typed_name_is_coerced_without_with_suffix_eating_the_convention` | survives | same name |
| `TestConventions::a_name_already_obeying_the_convention_is_returned_untouched` | survives | same name |
| `TestConventions::an_empty_clip_is_refused` | replaced | `an_empty_span_is_refused` — `Project.clip` is gone (`adr/detector-is-a-node.md`) but the crop record still says which source frames a written file covers, so `SourceSpan` keeps the check |

### `test_replicates.py` — 14 cases

| v2 case | Verdict | v3 case, or what removed it |
|---|---|---|
| `TestReplicate::identity_survives_rename` | survives | same name |
| `TestReplicate::identity_survives_geometry_change` | replaced | `identity_survives_a_geometry_edit` — geometry is now an override on the crop node's region param, so the claim holds at the place the box actually lives |
| `TestReplicate::distinct_replicates_get_distinct_ids` | survives | same name |
| `TestReplicate::an_override_read_out_cannot_be_written_back_in` | survives | same name |
| `TestReplicate::pinning_one_parameter_leaves_the_others_pinned` | survives | same name |
| `TestReplicateSet::append_returns_landing_position` | dropped | `ReplicateSet` is not carried — see below |
| `TestReplicateSet::index_of_finds_by_id` | dropped | same |
| `TestReplicateSet::index_of_raises_for_unknown_id` | dropped | same |
| `TestReplicateSet::remove_and_insert_are_inverses` | dropped | same |
| `TestReplicateSet::replace_returns_what_it_displaced` | dropped | same |
| `TestReplicateSet::as_list_is_a_snapshot` | dropped | same |
| `TestReplicateSet::default_names_count_up` | dropped | same |
| `TestReplicateSet::default_names_reuse_gaps` | dropped | same |
| `TestReplicateSet::custom_names_do_not_consume_default_numbers` | dropped | same |

### Six v3 cases with no v2 row

23 cases land in `test_pipeline_model.py` and 7 in `test_replicates.py`: 19
and 5 carried from the rows above, plus these.

`an_edge_from_a_node_to_itself_is_refused` pins a validator v2 had and v2's
file did not cover. `TestCropRecords` (three cases) covers `backs` and the
one-record-per-cut rule, which this item's body names as what the fields must
be able to say and which v2 tests from `pipeline/` rather than here.
`a_pin_does_not_reach_the_replicate_it_was_copied_from` and
`pruning_keeps_only_deviations_that_still_name_a_node` cover copy-on-write and
`with_overrides_limited_to`, both carried and both untested in v2's file.

## What the drops cost, and what revives them

`equivalence_groups` answered "which of these twelve arenas are actually the
same run" by fingerprinting resolved params. Under
`adr/detector-is-a-node.md` a replicate's box *is* a resolved param, so every
replicate deviates on the crop node and the column would read (1, 2, 3, …)
for every project — which is the failure v2's
`geometry_and_naming_are_not_what_makes_a_group` was written to prevent.
Excluding the region would mean knowing which node is the crop, and this layer
is registry-blind by the same docstring that forbids resolving `tool_id`. So
the function is not carried, and Phase 7 — its only consumer, the replicate
table — is where that question gets answered rather than here.

`ReplicateSet` is a mutable ordered container whose whole surface returns what
it displaced so the GUI can construct an inverse. Phase 7 does undo as two
stacks of whole immutable pipeline values rather than command inversion
(PLAN.md), so the shape it exists to serve is the one v3 replaced.
`Project.replicates` is an ordered tuple and `with_replicates` sets it.

`Project.visited` — the geometry lock, recording which replicates had been
opened in the tab v2 tuned a step from — has no test among the 39 and no
consumer: that tab is on SCAFFOLD.md's absent-by-decision list.

## Two edits outside the module

`pyyaml` moves from the dev group to `dependencies`: the document is the
cluster handoff, so a headless install that cannot parse one cannot run.
`core/types.py`'s `ROI` docstring cited `Replicate.roi` and `CropParams.roi`
as its two coordinate spaces; the first no longer exists, so it names
`CropRecord.region` and the crop node's param instead. That is this item's
change making the sentence wrong, not a sweep.

## Criterion

```
$ uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_replicates.py -q
............................................                             [100%]
44 passed in 0.18s
```

`ruff check`, `lint-imports` (5 contracts kept) and the full `pytest -q` (193
passed) are green with it.

## Reopened at review, 2026-08-07

The table above and the criterion both stand; the module has two defects the
criterion cannot see, and both are in the mechanism this item introduced.

`frozen=True` is one level deep. `override_for`, `with_override` and
`resolved_params` all copy the outer mapping and alias the inner one, so
`params_for(crop, r1)["region"]["x"] = 999` writes into the frozen document —
and the crop node's region is a mapping precisely because
`adr/detector-is-a-node.md` moved the geometry there. Measured in
`findings/2026.08.07-frozen-is-one-level-deep-and-the-region-is-two.md`;
`test_an_override_read_out_cannot_be_written_back_in` misses it because its
value is a scalar while `make_project`'s representative override is not.

Ten of the module's eleven refusals survive being replaced with `pass` with the
criterion green — the stale-sink check, four duplicate-id checks, three
non-empty checks, the sink format pattern, and the negative-span-start check.
None had a v2 row, which is why the table did not surface them
(`findings/loop/2026.08.07-a-re-derivation-table-certifies-v2s-coverage-not-v3s.md`).
`test_replacing_the_graph_catches_stale_checkpoints_and_sinks` names sinks and
asserts nothing about them.

## Closed at rework, 2026-08-07

**Immutability is structural, not a read-boundary rule.** The finding's open
question was deep-copying at each read against storing params already-immutable;
the second is what shipped. A read boundary is a list of methods somebody has to
remember to extend, and `params_for` is on the interactive path and is read
again per node per replicate whenever a key is built, so the copy would be paid
on every drag of a slider rather than once at validation.

The obvious immutable mapping does not survive this module, which is what the
finding's caveat was pointing at: `MappingProxyType` in an `Any`-typed field
makes `model_dump(mode="json")` raise `PydanticSerializationError`, so the
document would be immutable and unsavable. `FrozenMapping` and `FrozenSequence`
are `dict`/`list` subclasses that refuse every write, which leaves pydantic
serializing them as what they are, `ser_json_inf_nan="constants"` reading the
same values, and a stored list still equal to the literal it round-tripped from
— a tuple would not be. `extra="forbid"` never entered it: params are an
`Any`-typed field's *contents*, not a field. `frozen_value` is applied in the
two field validators and in the three methods that reach the model through
`model_copy`, which runs no validator.

`FrozenSequence` was not covered until the mutation sweep said so: only the
region case had a test, and a band list is the other container a tool's
parameters carry.

**Each refusal now has a case that fails without it.** Six added — the stale
sink reference, the four duplicate-id checks, and the sink format pattern — plus
`TestBlankStringsAreRefused` for the three blank-string checks and a negative
span start beside the empty-span case.
`test_replacing_the_graph_catches_stale_checkpoints_and_sinks` cleared
`checkpoints` and `outputs` in one step, so nothing depended on the sink check
existing; it now clears them one at a time and asserts the refusal between.

Verified by mutation rather than by reading: each of the module's 22 `raise`
statements replaced with `pass` in turn, criterion re-run, tree restored with
`git checkout --`. All 22 are now caught; before this work, ten were not.
The commit that ran the sweep was made first, because `git checkout --` restores
to `HEAD` and takes uncommitted work with it.
