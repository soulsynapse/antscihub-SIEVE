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
