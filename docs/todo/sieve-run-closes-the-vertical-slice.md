---
title: sieve run closes the vertical slice
step: "03.8"
status: done
gated_on: nothing
done_when: "uv run pytest tests/integration/test_cli_run.py -q"
opened: 2026-08-06
---

# sieve run closes the vertical slice

A minimal `sieve run` over an inline/YAML pipeline: one tool, one video, end
to end on `synthetic_video` — Phase 3's gate made a command. Port-with-rename
from v2's run command, cut to what the ported `test_cli_run.py` exercises;
the full CLI is Phase 5 and nothing beyond `run` comes now. Headless is a
contract, not a hope: the command imports no Qt, and the `.importlinter`
`headless` list already says so (00.2).

## The case table

v2's `tests/integration/test_cli_run.py` holds **six** cases. It cannot be
ported unrewritten — every one of them constructs `ClipRange`, `Replicate(roi=)`
or `filter_id=`, and fails at import before reaching an assertion — so the
re-derivation rule applies and this is its table. Four rows survive, two drop.

| v2 case | v3 |
|---|---|
| `two_replicates_run_and_the_second_reuses_the_first` | **replaced by** the same-named case. v2 gave both replicates one `roi` to make the keys coincide; schema v1 has no `Replicate.roi` (`adr/detector-is-a-node.md`), so two replicates that override nothing are the same claim in its plainest form. |
| `a_hand_written_crop_node_runs_with_no_replicates` | **dropped** — `crop` is a Phase 4 tool and this build's shelf holds one tool. |
| `a_hand_written_span_node_narrows_what_the_project_asked_for` | **dropped** — same, `span` is Phase 4. `plan.py`'s `_selected` is the machinery and `tests/unit/test_plan.py` covers it; what is missing is a *registered* selecting tool, which this item does not land. |
| `a_dry_run_never_opens_the_video` | **replaced by** the same-named case. Its second half tested a project with the clip cleared; schema v1 records none at all, so it becomes "no `--frames`", which is every unspanned project rather than a hand-edited one. |
| `declared_outputs_are_refused_rather_than_ignored` | **survives** verbatim in substance. |
| `a_filter_this_build_does_not_have_is_named_before_anything_decodes` | **survives** as `a_tool_this_build_does_not_have_...` (`adr/tools-not-filters.md`). |

## Reopened by review, 2026-08-07

Two cases short, and both are the ordinary invocation rather than an edge. The
four cases that landed build every project the same way — always with at least
one `Replicate`, always invoked with `--frames` — and that uniformity leaves two
production branches which no test can tell from nonsense. Verified by mutation
against the criterion, both still green:

- `_targets` reduced to `tuple(project.replicates)`, dropping `or (None,)`. A
  project with no replicates then runs nothing, prints nothing, and exits 0.
  This is the plain invocation, and it is the claim v2's
  `a_hand_written_crop_node_runs_with_no_replicates` carried — the table dropped
  that row for its *tool*, but the row's claim is about the baseline, and
  `downsample` serves it.
- `span_for`'s fallback replaced with `SourceSpan(start=0, end=1)`. This is the
  branch the commit subject names — the span is the flag *or the whole video* —
  and the whole video half has never run.

Add both cases: a project with no replicates whose output line is labelled
`baseline`, and an invocation with no `--frames` that covers `FIXTURE_FRAMES`
frames (`tests/conftest.py`). `done_when` is unchanged; it covers them.

Not required, and named so the next run does not go hunting: the lead-in
shortfall warning and `load_project`'s `ValidationError` refusal also survive
mutation. The first is unreachable with a one-tool shelf that declares no
lead-in, and the second has no v2 row. Both come back with the tools of Phase 4
and the full CLI of Phase 5.
