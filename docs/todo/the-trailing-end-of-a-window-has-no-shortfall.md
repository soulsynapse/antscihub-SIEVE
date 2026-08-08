---
title: The trailing end of a window has no shortfall
priority: normal
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_plan.py tests/unit/test_executor.py tests/integration/test_cli_run.py -q -k trailing_shortfall"
opened: 2026-08-07
---

# The trailing end of a window has no shortfall

`ExecutionPlan` widens the decode range at both ends and reports
`lead_in_shortfall` at one. The asymmetry is forced rather than chosen: frame
zero is the floor on every machine, so lead-in reaching before it is knowably
unavailable, while how many frames the footage holds is a fact about a container
`plan.py` may not open. So a run whose last frames want lookahead past the end
of the video asks for it, and the reader returns fewer frames than the range
named.

What is undecided is who answers for that, and it is a real question rather than
a tidiness one: the frames at the end of a span are computed from a window that
ran off the end, which is the same silent-wrong-answer shape `lead_in_shortfall`
exists to make visible at the other end — a plausible frame, no error, and the
tuning done against it wrong rather than absent.

Three candidates. The executor discovers it, having opened a reader, and reports
it per run. `resolve_source` (Phase 5) knows a crop artifact's span exactly and
could hand the plan a ceiling the way Phase 5 hands it a floor. Or the answer is
that a trailing shortfall is not a defect at all, because the last frames of a
video have no later frames in any run and refusing them would make the end of a
video untunable — which is `decode_start`'s argument, and if it holds here then
what is missing is only the *report*.

Gated on nothing, but 03.6 is where it will first be met.

## Met at 03.6, and it is not a shortfall

The reader does not return fewer frames than the range named: `VideoReader.read`
refuses an index at or past `frame_count` outright, and the loop reads every
frame of `decode_range` with no branch for a reader that cannot supply one. So
the run raises rather than running short
([findings/2026.08.07-a-lookahead-at-the-end-of-a-video-is-a-decode-error.md](../findings/2026.08.07-a-lookahead-at-the-end-of-a-video-is-a-decode-error.md)).

That prices the third candidate. "The answer is only the *report*" was the
cheapest of the three and it is not free: nothing currently runs short, so
somebody has to stop the loop at what the reader has before there is anything to
report. It also sharpens the symmetry argument — `decode_start` clamps because
refusing would make the opening seconds of every video untunable, and refusing
is exactly what happens at the other end today.

## This is the decision, and the failure that prices it is filed elsewhere

[a-detector-cannot-run-to-the-end-of-its-own-footage.md](a-detector-cannot-run-to-the-end-of-its-own-footage.md)
is the same question with a user in front of it: `sieve run` over a project
holding a `detect` node with no `--frames` refuses the whole run with
`arena-1: Frame 40 out of range 0..39`, which is the default invocation of the
only graph shape Phase 4 built the contract for. It argues the first candidate
above — narrow the span, name how many frames were dropped and why, keep the
refusal for the case where nothing is left — and names `cli/run_cmd.span_for`
as the caller that has opened a container and so is the one that can answer.

Two items, one decision, and this one drains first: phase 3 before phase 5.
So the session that takes this owes the answer for both, and should read that
item before choosing among the three candidates — it carries the concrete
failure, the proposed reading, and the observation that
`tests/integration/test_v2_oracle.py` already works around the gap by deriving
its span from the declared lookahead. Whichever way this goes, that item is
closed against it or narrowed to the message alone.

## The criterion pins the report, which is what all three candidates end in

Cases spelling `trailing_shortfall`, in whichever of
`tests/unit/test_plan.py`, `tests/unit/test_executor.py` and
`tests/integration/test_cli_run.py` the answer puts them — all three named, so
the criterion does not pick the candidate. What it does pick is that the
shortfall is *named*, because that is the one thing the three agree on: the
executor discovering it reports it per run, `resolve_source` handing the plan a
ceiling makes it a plan field beside `lead_in_shortfall`, and even the reading
that a trailing shortfall is no defect was priced by the 03.6 amendment above
into "somebody stops the loop at what the reader has and says how many frames
that cost". A run that silently narrows its span is refused by this criterion
as firmly as one that still dies with `Frame 40 out of range 0..39`.

## Folded in 2026-08-08: the decision is made, and two callers did not get it

The phase-5 item above landed first, as its own last section said it would, and
it took the second candidate: `ExecutionPlan.build` takes an optional
`source_end`, `sieve run` opens the container once to supply it, and given one
the span narrows to the last frame the lookahead can be filled behind while
`ExecutionPlan.trailing_shortfall` says how many frames that cost. The empty case
refuses. `SOURCE_FRAME_ZERO` is the floor the ceiling is now symmetric with, and
`findings/2026.08.07-a-lookahead-at-the-end-of-a-video-is-a-decode-error.md`
carries a dated amendment saying what is still true of a plan handed no ceiling.

What is left for this item is the callers that hand none, since for them the
finding is still exactly what happens:

- `PreviewSession` builds its own plan and passes no ceiling, so a preview
  window reaching the last frames of a video under a centred detector still dies
  with `Frame N out of range`. It holds a `FrameSource` rather than a container
  and cannot ask one how long the footage is, so this is the question of whether
  `FrameSource` grows a length — which is also what `resolve_source` would need
  to hand a *crop artifact's* ceiling over, the candidate this one names.
- `tests/integration/test_v2_oracle.py` still derives `SPAN` from the declared
  lookahead, and its module docstring and
  `test_the_span_is_the_widest_the_footage_can_answer_for` both explain that
  derivation by "the plan does not clamp it". True of the plan the oracle builds
  and no longer true of the command it invokes: passing `--frames 0:29` and
  passing nothing now produce the same run, and the workaround has become a
  pinning of a number that the run would arrive at by itself.

Neither is covered by the criterion below, which is about the shortfall being
named — a thing that now happens, in one of the three files, under the other
item's spelling.

Deliberately not pinned: whether the run completes or refuses when nothing is
left, and where the number is computed. The first is the phase-5 item's
sentence — keep the refusal when the span empties — and the second is the
choice among the three. The integration file is in the command so that the
answer can be proven at the invocation that fails today rather than only at the
layer that computes it; if the answer turns out to be entirely inside
`plan.py`, the two unit files carry it and the third contributes nothing, which
costs a collection and no coverage.
