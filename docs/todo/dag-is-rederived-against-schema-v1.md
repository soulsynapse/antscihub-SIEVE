---
title: dag is re-derived against schema v1
step: "03.3"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_dag.py -q"
opened: 2026-08-07
---

# dag is re-derived against schema v1

`pipeline/dag.py` — 907 lines, the largest single module in the port —
re-derived against schema v1 (02.1) under PLAN.md's re-derivation clause: the
algorithm is copied line for line, the types are v3's, and the case table is
what stands in for "port the test file first".

`tests/unit/test_dag.py` holds **33 cases in 15 classes**, and this item's
table has 33 rows. Two things come out of the v2 signatures on the way, and
both are decisions already made rather than this item's to take: `Backend` is
a parameter of `Dag.build` and goes with `backend/`
(`adr/no-kernel-apparatus.md`), and `LoweredPrefix` goes with
`pipeline/lowering.py`, which PLAN.md does not build until a budget is missed.
A case whose subject is either of those is *dropped* citing that decision; a
case about edge legality, cycles, port wiring, or type agreement *survives*
and is the reason this module is being copied rather than rethought.

`graph_needs_chroma` is here, and the format contract it belongs to is a
separate pool item
(`the-decode-executor-format-contract-is-rederived.md`) — this item re-derives
the function, not the contract test.

The v2 deferral that produced this split is in
`findings/2026.08.07-v2s-pipeline-does-not-separate-from-its-schema.md`: the
three graph modules and the executor were one item, and 907 + 328 + 430 + 428
lines with four re-derivations under them is not one session's work.

## The case table

33 rows, one per v2 case in `tests/unit/test_dag.py` — 33 test functions in 8
classes, not 15; the class count above is wrong and the case count is right.
Three verdicts, as 02.1's table used them: *survives* — same claim, same name,
only the fixture rewritten into schema v1's vocabulary; *replaced* — the claim
survives but is aimed at a different subject, and the v3 case is named;
*dropped* — the subject is gone, citing what removed it.

Three rules do the dropping, and none is this item's decision.
`core/tool_base.py` cut the input-port protocol until the first two-input tool,
so an edge has no port, a node has one input, and no graph here can merge —
which is the rule this item's body did *not* name and which does most of the
work below (see the note after the table). `backend/` is dropped outright
(`adr/no-kernel-apparatus.md`). And `pipeline/cache_key.py` is 03.4, one step
after this one, so `Dag.node_keys` — whose two non-obvious parameters are the
`Backend` and the `LoweredPrefix` this item's body already drops — is not
written here; it lands with the key it folds
(`todo/the-key-walk-rejoins-the-graph.md`).

| v2 case | Verdict | v3 case, or what removed it |
|---|---|---|
| `TestRejections::a_cycle_names_every_node_that_could_not_be_ordered` | survives | same name |
| `TestRejections::a_missing_filter_is_named_by_id_and_version_all_at_once` | survives | `a_missing_tool_is_named_by_id_and_version_all_at_once` (`adr/tools-not-filters.md`) |
| `TestRejections::rows_may_not_feed_an_input_that_wants_frames` | survives | same name; the port assertion goes with the port |
| `TestRejections::an_edge_into_a_port_the_filter_does_not_declare_is_refused` | dropped | no port to misspell — the input-port protocol is cut |
| `TestRejections::a_declared_port_left_unfilled_is_refused` | dropped | same: a non-root node has exactly one incoming edge and `Pipeline` refuses a second |
| `TestRejections::a_merging_filter_cannot_sit_at_a_root` | dropped | same: no tool declares two inputs, so no tool can be a merging root |
| `TestValidate::the_first_diagnostic_is_the_error_build_raises` | survives | same name; `BROKEN` drops its three port entries and keeps cycle, unresolved, edge type |
| `TestValidate::a_graph_that_validates_clean_is_one_build_accepts` | survives | same name, over `fan_out()` |
| `TestValidate::two_independent_faults_are_both_reported` | replaced | same name, two mistyped edges in disconnected halves of one document — with wiring verdicts gone, edge types are the only rejection that collects |
| `TestValidate::an_unresolved_filter_reports_every_node_naming_it` | survives | `an_unresolved_tool_reports_every_node_naming_it` |
| `TestValidate::nothing_is_reported_that_a_missing_spec_would_have_to_be_guessed_from` | survives | same name, over a chain instead of a merge |
| `TestValidate::a_node_whose_wiring_is_broken_gets_no_second_verdict_about_its_types` | dropped | there is no wiring verdict to suppress a type verdict, so `_edge_faults` has no `skip` set |
| `TestValidate::a_mistyped_edge_names_both_ends_it_could_be_repaired_from` | survives | same name |
| `TestOrder::the_order_follows_the_document_and_not_when_a_node_was_freed` | survives | same name |
| `TestOrder::every_node_comes_after_its_upstreams` | survives | same name; `fan_out()` replaces the diamond and the leaves are two |
| `TestKeyWalk::the_walk_is_the_hand_walk` | dropped | `node_keys` is not in this module yet — it needs 03.4's `node_key` and `source_key` |
| `TestKeyWalk::swapping_a_merges_ports_moves_its_key_and_only_its_key` | dropped | ports *and* the walk: the asymmetry it pins is `cache_key.py`'s and has no expression without a merge |
| `TestKeyWalk::an_uncacheable_node_takes_its_descendants_and_nobody_else` | dropped | same walk; the claim is 03.4's to restate when the walk lands |
| `TestElementMeaning::the_source_is_pixels_and_a_preserving_root_says_so` | survives | same name |
| `TestElementMeaning::meaning_carries_through_every_preserving_node_after_a_redefinition` | survives | same name |
| `TestElementMeaning::aggregating_blocks_loses_the_meaning_and_it_never_returns` | survives | same name |
| `TestElementMeaning::a_merge_of_two_meanings_resolves_to_neither` | dropped | no merge is expressible; the branch in `_elements` that disagreeing upstreams resolved is gone with it |
| `TestElementMeaning::a_table_emitter_has_no_element_at_all` | survives | same name |
| `TestSourceIndexing::a_rate_change_unindexes_itself_and_everything_after_it` | survives | same name |
| `TestSourceIndexing::a_graph_with_no_rate_change_is_indexed_throughout` | survives | same name |
| `TestWhereMeaningWasLost::it_names_the_node_that_lost_it_not_the_one_that_asked` | survives | same name |
| `TestWhereMeaningWasLost::the_earliest_loss_wins_when_a_chain_loses_it_twice` | survives | same name |
| `TestWhereMeaningWasLost::a_sibling_that_kept_its_meaning_is_not_blamed` | replaced | `a_branch_that_does_not_feed_the_asker_is_not_blamed` — v2 needed a merge to make the sibling reach the asker; a fan-out branch that loses its meaning *earlier in the order* is what makes a whole-graph scan give the wrong node, which is the claim |
| `TestWhereMeaningWasLost::asking_about_a_node_that_has_a_meaning_is_refused` | survives | same name |
| `TestLinearOrder::the_order_is_the_edges_and_not_the_declaration` | survives | same name |
| `TestLinearOrder::a_chain_of_filters_nobody_has_installed_still_orders` | survives | `a_chain_of_tools_nobody_has_installed_still_orders` |
| `TestLinearOrder::a_diamond_is_refused_though_it_executes_fine` | replaced | `a_branch_is_refused_though_it_executes_fine` — the seam between the two walks is what the case is for, and fan-out is the whole of it that schema v1 can write |
| `TestLinearOrder::a_cycle_off_the_root_is_refused_as_disconnected` | survives | same name |

Twenty-two survive, three are replaced, eight are dropped. The eight are seven
port-or-merge cases and one walk that is not here yet, and the arithmetic is
the visible consequence of a decision taken in 01.2 rather than a shrinking
scope: v2's file spent a quarter of itself on a protocol v3 does not have.

**The body's survivor list names port wiring, and schema v1 has no ports.** The
sentence was written against v2's five rejections; v3 has three, and the fourth
did not weaken — it moved. "Two edges feed one node" is `Pipeline`'s validator
(02.1) and is tested in `test_pipeline_model.py`, so the check is stronger than
v2's and lives one layer down, where it is structural rather than a graph
question. Nothing else was read past that.

## Eight v3 cases with no v2 row

Twenty-five of v2's 33 rows carry over and eight cases here have no v2 row at
all, so `tests/unit/test_dag.py` holds 33 functions again — the same total by
arithmetic accident, not by matching v2 case for case. `needs_chroma` and `graph_needs_chroma` are in
this module and v2's file never touched either — v2 tested the format decision
from the callers that consumed it — so `TestDecodeFormat` covers the four
answers `_requires_chroma` can give (silence, a colour-only set, a set that
still admits GRAY, a row consumer) plus the unresolvable graph that falls back
to colour. `TestLookups` proves the `KeyError` both queries declare
(`todo/a-lookup-that-declares-a-keyerror-proves-it.md`). And the empty graph
gets a case in each walk: `Dag.build` over no nodes has no roots to name, and
`linear_order`'s root count would refuse a graph that has no root because it
has no nodes — the shape a project has before anything is on its canvas.
