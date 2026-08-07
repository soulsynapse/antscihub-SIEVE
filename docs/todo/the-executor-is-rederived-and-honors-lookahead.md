---
title: The executor is re-derived and honors lookahead
step: "03.6"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_executor.py tests/unit/test_stateful_execution.py -q"
opened: 2026-08-06
---

# The executor is re-derived and honors lookahead

`pipeline/executor.py` re-derived against schema v1 under PLAN.md's
re-derivation clause, plus the one reviewed extension: emission delayed by
declared lookahead, a centered window being warmup + lookahead.
`tests/unit/test_executor.py` and `test_stateful_execution.py` hold **13 and
8 cases**, and this item's table has 21 rows. The algorithm is copied line for
line and the delay is the only intended change to it; `backend/dispatch.py`'s
binding is what comes out, and `Node` is schema v1's.

`pipeline/cache.py` lands here verbatim — 114 lines over `core.types`, the
store keyed by `(node key, source frame index)` that this loop writes into.
It is the one file in this item that is a byte-identical port, and its
docstring's argument for that key shape is the reason it is not re-derived
with everything else.

State stays minted per run from the spec-declared factory and branching stays
on declared shape, never `tool_id` (`adr/no-kernel-apparatus.md`). New emission-delay tests join
`test_executor.py` with `lookahead` in their names.

Added at 01.2's review, 2026-08-07: **`run` joins `ToolSpec` here.** 01.2 cut
it — declared-means-verified refuses a field whose only reader is two phases
out — so ADR-2's "the spec points at it" is unimplemented, and this is the
step whose reader makes it implementable. Without the field the executor has
to find a tool's `run` by its id, which is precisely the file-that-grows-with-
the-tool-count ADR-2 exists to prevent — and the alternative is carrying
`backend/dispatch.py`'s scaffolding across to fill the gap.

Undeferred 2026-08-07 by the phase readjustment: the blockers were
`plan.py`, schema v1 and `pipeline/cache.py`, and all three now land ahead of
this step — 02.1, 03.5, and this item respectively. The deferral was correct
arithmetic on a plan that put the graph before the schema, and the plan is
what changed.

## The case table

21 rows, one per v2 case: 13 in v2's `test_executor.py` and 8 in v2's
`test_stateful_execution.py`, which are the counts this item states up front as
PLAN.md's re-derivation clause asks. The v3 files are a different count and it
is the one `done_when` reports: **13 and 7**, being 21 rows less the 6 dropped
plus the 5 delay cases below, so 20. Three verdicts, as 03.3, 03.4 and 03.5 used
them: *survives* — same claim, only the fixture rewritten into v3's vocabulary;
*replaced* — the claim survives but is aimed at a different subject, and the v3
case is named; *dropped* — the subject is gone, citing what removed it.

Six of the twenty-one are dropped and five of those six are one decision applied
five times. `backend/` does not come over (`adr/no-kernel-apparatus.md`), so
there is no preference order, no per-node backend, no second registry pairing a
callable with a state factory, and nothing for a key to hash about a device. The
sixth is the merging protocol, which schema v1 cannot express — `Pipeline`
refuses a second edge into one node — and which
[a-merge-keys-its-inputs-by-port](a-merge-keys-its-inputs-by-port.md) holds,
deferred on the first two-input tool.

One fixture-level substitution runs through both files and is not a verdict on
any row. v2's cases stand on `sieve.filters`: `test_executor.py` registers four
of its own onto a scratch shelf, and `test_stateful_execution.py` uses the real
`background_ema`. There is no shelf at 03.6 — the first tool is 03.7 — so both
v3 files declare the tools they need, the background model included. A case that
named the first real tool would be asserting against that tool rather than
against the contract the loop reads, which is `test_plan.py`'s reason for the
same choice.

### `tests/unit/test_executor.py`

| v2 case | Verdict | v3 case, or what removed it |
|---|---|---|
| `the_lead_in_reaches_the_kernel_and_not_the_caller` | survives | `the_lead_in_reaches_the_run_and_not_the_caller` — one plain `run` per tool is what a kernel was (`adr/no-kernel-apparatus.md`) |
| `a_warm_cache_skips_the_kernel_and_the_decode` | survives | `a_warm_cache_skips_the_run_and_the_decode` |
| `every_root_sees_the_replicates_crop_on_every_frame` | replaced | `two_roots_share_one_decode_of_each_frame` — the crop is a node and its region never reaches this module (`adr/detector-is-a-node.md`); what the case also pinned, that a second root costs a second call and not a second read, is the loop's own claim and is what the v3 case keeps |
| `the_decoded_frame_escapes_uncropped_and_only_when_a_decode_happened` | replaced | `the_decoded_frame_reaches_the_caller_only_when_a_decode_happened` — "uncropped" has no subject for the row above's reason, and with it goes `FrameResult.source_cropped`; the two claims that remain are that the frame is this result's and that a warm replay carries none |
| `a_windowed_node_gets_a_span_ending_at_the_current_frame` | survives | same name |
| `a_windowed_merging_node_is_still_refused_before_anything_is_read` | replaced | `a_node_the_one_signature_cannot_call_is_refused_before_anything_is_read` — the shape it named cannot be built, and the claim is about refusing *before a frame is read*, which is asserted over the four shapes `ToolRun` cannot call |
| `a_merging_node_gets_a_frame_per_port_and_the_ports_mean_something` | dropped | there are no ports: `accepts` is one stream and an edge names none (`core/tool_base.py`), and [a-merge-keys-its-inputs-by-port](a-merge-keys-its-inputs-by-port.md) is deferred on the tool that would restore them |
| `a_merge_below_branches_of_unequal_warmup_sees_aligned_settled_inputs` | replaced | `every_node_in_a_result_answers_for_the_same_source_frame` — there is no merge for alignment to be checked at, and the delay gives the claim a new way to break that v2's loop did not have: a fork whose branches lag differently answers one frame at two different steps |
| `the_backend_is_pinned_to_the_plans` | dropped | `adr/no-kernel-apparatus.md` — nothing is selected, so nothing can be selected wrongly |
| `a_gpu_run_is_not_served_the_cpu_runs_cache_entries` | dropped | same; the backend was the sixth position of v2's node key and Phase 1 cut it (`findings/2026.08.07-v2s-pipeline-does-not-separate-from-its-schema.md`) |
| `one_graph_can_span_two_backends` | dropped | same |
| `a_backend_mapping_missing_a_node_is_refused` | dropped | same — `ExecutionPlan.build` takes no backend |
| `a_node_with_no_kernel_for_the_plans_backend_says_so` | replaced | `a_spec_that_points_at_no_run_says_which_node` — "no kernel for this backend" splits into "no GPU wheel" and "no GPU kernel written", and neither exists; what survives is that the executor names the node and the tool rather than swallowing the refusal |

### `tests/unit/test_stateful_execution.py`

| v2 case | Verdict | v3 case, or what removed it |
|---|---|---|
| `a_stateful_node_gets_no_cache_key_and_writes_no_entry` | survives | same name |
| `a_correct_warmup_is_what_makes_two_spans_agree` | survives | same name |
| `a_filter_whose_warmup_is_a_lie_disagrees_with_itself_across_spans` | survives | `a_tool_whose_warmup_is_a_lie_disagrees_with_itself_across_spans` (`adr/tools-not-filters.md`) |
| `the_lead_in_is_what_settles_the_model` | survives | same name |
| `two_concurrent_runs_of_one_node_do_not_share_a_model` | survives | same name |
| `a_second_run_starts_cold` | survives | same name |
| `start_mints_a_state_per_call_and_leaves_stateless_kernels_alone` | replaced | `binding_mints_a_state_per_run_and_leaves_a_stateless_tool_alone` — there is no `KernelBinding.start` to call twice; `_bind` is what mints, and the second half of the claim is that a stateless tool's binding carries the registered function itself and no state |
| `a_stateful_kernel_behind_a_spec_that_does_not_declare_it_is_refused` | dropped | the pairing it policed was between two registries and one of them is gone (`adr/no-kernel-apparatus.md`); the factory is a spec field now and 01.2's `test_a_state_factory_without_stateful_is_refused` is the same refusal at the only place left to make it |

### Five v3 cases with no v2 row

All five are the delay, and each carries `lookahead` in its name as the item
asks. `a_lookahead_node_emits_for_a_frame_it_has_already_read_past` is the
extension at the yield and `a_lookahead_window_holds_the_frames_on_both_sides_of_its_target`
is the same extension at the call — a loop that widened the decode range and
then handed over a trailing window anyway passes the first and fails the second.
`the_lookahead_the_loop_delays_by_is_the_one_the_plan_decoded_for` is the one
claim spanning two modules: the loop accumulates the lag forward from the roots
and the plan folds the maximum backward from the leaves, and nothing else checks
that the two agree.
`a_lookahead_tool_that_answers_for_the_end_of_its_window_is_refused` is the
executor's index check aimed at the mistake the convention invites, and
[a-centred-window-counts-its-target-from-the-wrong-end](a-centred-window-counts-its-target-from-the-wrong-end.md)
is the fix it stands in for.
`no_node_that_lags_behind_the_lookahead_is_ever_a_keyed_node` asserts a
disjointness rather than a behaviour, because the behaviour it was written for
cannot vary: filing a store entry at the reading index is an equivalent mutant
under the current cache policy
([findings/loop/2026.08.07-the-emission-delay-and-the-cache-key-cannot-meet.md](../findings/loop/2026.08.07-the-emission-delay-and-the-cache-key-cannot-meet.md)).

## What the delay cost the loop, and what it did not

The item calls the delay the only intended change to v2's algorithm, and it is
one change with three consequences that are worth naming because none of them is
visible at the line that applies it.

A node's output no longer belongs to the loop's own index. Each binding carries
a *lag* — its declared lookahead plus its upstream's — so at step `j` it answers
for `j - lag`, and a frame's result is assembled from calls made at up to
`plan.lookahead` different steps. That is the one new data structure: a dict of
partial results, at most `plan.lookahead` deep, drained in order as the slowest
node reaches each frame. v2 could yield inside the node loop because every node
answered for the frame being read.

The window is filled on every step its input arrives, including the steps before
the node may emit anything — those frames are the lookahead side of its first
window. So the "still filling" branch sits after the append and before the call,
not before the input, which is also why the cache lookup keeps v2's position at
the top: a windowed node never has a key to hit (`cache_key.CachePolicy.
WINDOWED_FRONTIER`), so nothing that gets served from the store has a history
that could develop a gap.

And rate-changing tools are refused rather than merely unimplemented, as in v2.
Two folds now count in source frames — the plan's and the loop's — and a node
that emitted at another rate would put them in different index spaces.

Two v2 mechanisms come over unchanged in shape and different in content.
`unrunnable_reason` moves out of `backend/dispatch.py` into the executor, where
its clauses are what the one signature cannot express rather than what four
protocols declined to invent; `run=None` joins them, which is what makes the
field's optionality safe rather than silent. And `BoundNode` is v2's
`KernelBinding` with the shelf under it gone: with one signature and no
backends, the only per-run thing left for it to hold is the state.
