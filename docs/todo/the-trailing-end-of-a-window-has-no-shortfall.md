---
title: The trailing end of a window has no shortfall
priority: normal
phase: 3
status: open
gated_on: nothing
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
