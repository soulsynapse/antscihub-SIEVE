---
title: The session layer holds the project and its two stacks
step: "07.2"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_session.py -q -k 'undo_restores_the_prior_whole_value or a_reopened_project_round_trips'"
table_rows: 17
cases:
  tests/unit/test_session.py: 8
opened: 2026-08-08
---

# The session layer holds the project and its two stacks

The Qt-free half of the skeleton lands first because everything else in the
phase writes through it. `session/` is a new top-level package holding the open
project as a schema-v1 value and undo/redo as two stacks of whole immutable
pipeline values — moving a pointer through values, never inverting a command,
with prefix reuse falling out of the executor's cache and no history-aware code
(`adr/gui-base-is-the-v25-spike.md`). The spike's `session/` is the seed and
its tests are the spec, under the re-derivation table rule from PLAN.md's
porting discipline: the spike's value types are not schema v1, so every spike
case is a row that survives, is replaced by a named v3 case, or is dropped
citing the decision that removed its subject.

The package's admission is already whole — the VISION.md row, the ownership
line on a declared-but-empty package (the Phase-0 pattern), the layers row
below `sieve.gui`, and `headless` membership, whose reds
`tests/unit/test_contract_lines_go_red.py` generates from the config — so
this item adds only contents. The row's never-cell is the standard: never Qt,
never a computation — the GUI renders what this holds, the pipeline computes
what this asks for.

## The re-derivation table (2026-08-08)

The spike's `session/` holds **17 cases** across four test files —
`test_history.py` 5, `test_session.py` 5, `test_app_state.py` 4,
`test_frames.py` 3 — read at `rewrite:proto_sieve/src/sieve/session/`. Every
one is a row. v3's cases all live in `tests/unit/test_session.py`, because
what the spike split across `History` and `Session` is one thing here: the two
stacks were a module of their own only to keep the draft and the step index
out of them, and both of those are dropped below.

| Spike case | Verdict |
|---|---|
| `history: undo_returns_the_previous_committed_value` | replaced by `undo_restores_the_prior_whole_value` |
| `history: redo_returns_the_value_undone_away_from` | replaced by `redo_returns_the_value_undone_away_from` |
| `history: undo_at_the_start_of_history_is_a_no_op` | replaced by `undo_with_nothing_committed_is_a_no_op` |
| `history: push_after_undo_discards_the_redo_branch` | replaced by `a_commit_after_an_undo_discards_the_redo_branch` |
| `history: can_undo_and_can_redo_track_stack_state` | replaced by `can_undo_and_can_redo_track_the_two_stacks` |
| `session: edit_does_not_change_the_committed_pipeline` | dropped — the draft, see below |
| `session: commit_replaces_the_current_step_and_pushes_history` | replaced by `can_undo_and_can_redo_track_the_two_stacks` for the push; the step-replacement half goes with the draft |
| `session: commit_with_no_draft_is_a_no_op` | dropped — the draft |
| `session: select_discards_a_staged_draft` | dropped — the draft and the step index |
| `session: undo_reverts_a_commit_and_clears_any_draft` | replaced by `undo_restores_the_prior_whole_value`; the draft clause has no subject |
| `app_state: select_produces_a_project_active_state` | dropped — no project chooser in the first cut |
| `app_state: select_seeds_an_empty_pipeline_for_the_projects_source` | dropped — no project chooser in the first cut |
| `app_state: select_seeds_a_session_with_nothing_to_undo` | replaced by `a_freshly_opened_session_has_nothing_to_undo` |
| `app_state: no_project_is_a_distinct_state` | dropped — no project chooser in the first cut |
| `frames: index_minus_one_is_the_untouched_source` | dropped — a computation |
| `frames: each_index_reflects_only_the_steps_up_to_it` | dropped — a computation |
| `frames: stepping_reuses_the_executors_cache_for_the_shared_prefix` | dropped — a computation; the claim is `tests/unit/test_preview.py`'s |

The decisions behind the three groups of drops:

- **The draft and the step index.** 07.3 ratifies a kind list where every
  mutation "lands as a new whole pipeline value on the undo stack", so there is
  no uncommitted intermediate for a draft to be — and schema v1 has no `Step`
  for one to be shaped like. Which step is current is view state, which VISION's
  `gui` row owns.
- **`app_state`.** PLAN.md Phase 7: the first cut opens a project that exists
  and does not build one from a folder of videos, so `NoProject`/`select` would
  be a declaration with no consumer (`adr/declared-means-verified.md`). A
  session exists for an open project; what a front end shows before one is open
  is the GUI's.
- **`frames`.** The `session` row's never-cell refuses a computation, and the
  spike's `frames.py` stands on its `executor`/`lower` — the dissolved algebra
  (`adr/no-kernel-apparatus.md`). Its prefix-reuse claim is not lost: it is what
  `pipeline/preview.py` is written around and what `tests/unit/test_preview.py`
  asserts.

The spike's `history_timeline`/`history_index`/`jump_to` carried no case and
land nowhere: PLAN.md Phase 7 cuts the history dialog for making undo a visible
object, which is the opposite of two stacks of whole values.

Two v3 cases have no spike ancestor, because the spike's session never touched
a file — `a_reopened_project_round_trips` and
`saving_after_an_undo_writes_the_restored_value`. Holding the *open* project is
this row's job, and a project that cannot come back off disk as the document
the session was holding is not held.
