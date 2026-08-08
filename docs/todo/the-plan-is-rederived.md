---
title: The execution plan is re-derived
step: "03.5"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_plan.py -q && uv run pytest tests/unit/test_plan.py -q -k two_roots && uv run pytest tests/unit/test_plan.py -q -k output_rate"
table_rows: 14
opened: 2026-08-07
---

# The execution plan is re-derived

`pipeline/plan.py` re-derived against schema v1 and the two-sided window.
`tests/unit/test_plan.py` holds **14 cases in 6 classes**, and this item's
table has 14 rows.

This is where Phase 1's lookahead contract first has consequences. v2's
`_lead_in` walks the graph summing `input_warmup_frames` because a v2 window
only ever trailed; a v3 window has two sides, so the frames a node needs
before its first emission and the frames it needs after are both real and the
selected range is widened at both ends. The executor honours it by delaying
emission (03.6); this item is where the arithmetic is decided, and a case
that asserts a one-sided lead-in is *replaced by* a named v3 case rather than
dropped — the subject survives, the claim changes.

`CostEstimate` is not here: Phase 1 cut it and its consumer is VISION's
process screen, so a case whose subject is a cost estimate is *dropped*
citing `adr/declared-means-verified.md`. `Backend` and `LoweredPrefix` are
dropped the same way, on the decisions named in 03.3.

## The case table

14 rows, one per v2 case in `tests/unit/test_plan.py` — 14 test functions in 2
classes, not 6; the class count above is wrong and the case count is right,
which is 03.3's inherited miscount repeating
(`findings/loop/2026.08.07-the-run-that-corrected-an-inherited-miscount-wrote-its-own.md`).
Three verdicts, as 03.3 and 03.4 used them: *survives* — same claim, same
name, only the fixture rewritten into schema v1's vocabulary; *replaced* — the
claim survives but is aimed at a different subject, and the v3 case is named;
*dropped* — the subject is gone, citing what removed it.

The three cuts this item's body names — `CostEstimate`, `Backend`,
`LoweredPrefix` — remove no row. They are a module constant and two arguments
to `plan_for`, so what they cost is fixture material rather than a claim, and
every drop below is charged to something else. What does the dropping is one
rule applied three times: schema v1 makes a written crop a *child source* with
an identity of its own, so `pre_cropped` has nothing to flag, a `Replicate`
carries no region to suppress (`adr/detector-is-a-node.md`), and whose frame
numbering a file is in is the read-back path's question, which `PLAN.md`
builds in Phase 5.

| v2 case | Verdict | v3 case, or what removed it |
|---|---|---|
| `lead_in_is_the_longest_path_not_the_whole_graph` | survives | `TestTheWindowHasTwoSides::` same name; the two-port join becomes a fork, since schema v1 refuses a second edge into one node, and `max` still disagrees with `sum` |
| `lead_in_crosses_a_rate_change_in_source_frames` | survives | `TestTheWindowHasTwoSides::` same name |
| `TestSelection::a_selecting_node_narrows_what_the_caller_asked_for` | survives | same name |
| `TestSelection::the_decode_range_still_widens_by_the_lead_in` | replaced | `TestSelection::the_decode_range_still_widens_at_both_ends` — the claim is the pushdown's, and a v3 window has a trailing side for it to fail to widen |
| `TestSelection::where_the_node_sits_does_not_change_which_frames_are_kept` | survives | same name |
| `TestSelection::two_selections_intersect_and_an_empty_one_is_refused` | survives | same name |
| `TestSelection::a_selecting_node_is_hashed_like_any_other_node` | survives | same name |
| `params_are_validated_even_where_no_key_is_derived` | survives | same name |
| `a_clip_near_the_start_runs_under_warmed_rather_than_failing` | survives | `a_span_near_the_start_runs_under_warmed_rather_than_failing` — `clip` is a dead v2 word (`todo/v2-field-names-join-the-spelling-gate.md`) |
| `the_replicates_overrides_reach_the_resolved_params` | survives | same name, extended: the replicate must reach the *keys* as well as the params, which are two arguments to two calls inside `build` |
| `TestPlanningAgainstACropThatAlreadyExists::the_replicates_region_leaves_both_the_crop_and_the_key` | dropped | there is no `plan.roi` to leave and no replicate geometry to leave it — the box is the crop node's region parameter (`adr/detector-is-a-node.md`) |
| `TestPlanningAgainstACropThatAlreadyExists::the_overrides_survive_the_crop_leaving` | dropped | the crop never leaves: with no pre-cropped flag the claim is "overrides reach the resolved params", which is the row above |
| `TestPlanningAgainstACropThatAlreadyExists::lead_in_before_the_artifact_begins_is_a_shortfall_not_a_request` | dropped | the artifact's own frame floor arrives with the read-back path in Phase 5; the floor here is frame zero and the clamp is the row two above |
| `TestPlanningAgainstACropThatAlreadyExists::a_span_beginning_before_the_artifact_clamps_rather_than_raising` | dropped | same floor. Its subject was a `FrameCount` refusing to go negative under a property that promises a clamp, which cannot arise while the floor is zero and a `SourceSpan` starts at or above it |

Four v3 cases have no v2 row, and all four are the second side of the window
or the one question v2's file never asked:
`TestTheWindowHasTwoSides::lookahead_is_the_longest_path_not_the_whole_graph`,
`::lookahead_crosses_a_rate_change_in_source_frames`,
`::a_centred_window_widens_the_decode_range_at_both_ends`, and
`the_reader_format_is_the_graphs_answer_and_not_a_choice`. The first two are
the fold's two claims asserted against the *lookahead* fold rather than
inferred from the warmup one, because the two sides are separate code and a
lookahead fold that dropped `at_input_of` agrees with every lead-in number in
the file.

One v2 declaration is refused rather than carried: `root_paths` existed so a
property test could check the walk against brute-force path enumeration, and
under schema v1 a node has one input and therefore exactly one root path — the
enumeration *is* the walk. The walk is checked against `source_warmup_frames`,
the single-path definition it folds, taken over each chain of the fork by hand.

## Two more cases with no v2 row, amended in at review

`_fold` maximises over two collections and the fourteen cases reach one of
them. Every pipeline in the file has exactly one root, so the closing
`max(need[root] for root in dag.roots)` passes as `min`, and passes folding
over `dag.order` instead — measured in
[findings/loop/2026.08.07-a-fold-has-two-maxima-and-one-fork-fixture-exercises-the-inner-one.md](../findings/loop/2026.08.07-a-fold-has-two-maxima-and-one-fork-fixture-exercises-the-inner-one.md).
Separately, `_input_lookahead_frames`' refusal of a non-positive `output_rate`
— declared in its own `Raises:` and again in `ExecutionPlan.build`'s — is
deleted with every case still green.

Both are v3's own: v2's file has no row for either, so they arrive as additions
rather than as verdicts. `done_when` selects them by substring, so the
substrings are the requirement and the sentences below only say what each must
assert (`findings/loop/2026.08.07-a-k-selector-and-the-prose-name-beside-it-are-two-criteria.md`).

- A case whose name contains **`two_roots`**: two roots with unequal windows —
  `Pipeline(nodes=(node("a", "settle1"), node("b", "settle5")))` builds with no
  edges and has both — asserting the graph's `lead_in` is the larger. That kills
  `min` and *not* a fold ranged over `dag.order`, so the case needs a second
  pipeline: the clause once written here — "the two roots must also be the two
  extremes of `need`" — is the condition under which the `dag.order` mutant is
  equivalent rather than dead, since `need` is non-decreasing towards a root
  while every rate is at or below 1. A root emitting *more* than it consumes is
  what separates the two collections
  ([findings/loop/2026.08.07-the-two-root-fixture-kills-one-mutant-of-two-and-the-second-needs-a-rate-above-one.md](../findings/loop/2026.08.07-the-two-root-fixture-kills-one-mutant-of-two-and-the-second-needs-a-rate-above-one.md)).
- A case whose name contains **`output_rate`**: a node whose `output_rate()`
  returns zero or less, reaching the *lookahead* fold, refused with the
  `ValueError` `build` declares — and asserted against `_input_lookahead_frames`
  itself, because the warmup twin carries character-identical text and is folded
  first, so a refusal asserted only through `build` is answered by the twin and
  survives its own deletion (same finding). The twin in `core/tool_base.py` is
  untested too and is outside this item —
  `todo/a-declared-refusal-that-only-the-lookahead-side-proves.md` holds it.
