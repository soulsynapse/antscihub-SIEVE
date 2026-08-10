---
title: The trailing end of a window has no shortfall
priority: normal
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_cli_preview.py -q -k \"trailing_shortfall and preview\""
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
it took the *shape* of the second candidate under the actor the first names —
the section above says that item "argues the first candidate", and both readings
are partly right, which is why neither number is the useful sentence. What
landed is: a caller with a container already open hands the plan a ceiling
(candidate two's mechanism), and the caller is `cli/run_cmd`, not
`resolve_source` (candidate one's actor). `resolve_source` handing a crop
artifact's ceiling over is still unbuilt and is part of what this item has left.
Concretely: `ExecutionPlan.build` takes an optional
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
  `preview_cmd` makes this visible from the outside: it now calls
  `run_cmd.footage_end` on every invocation to feed `span_for`, so it opens a
  container, learns the one number `PreviewSession`'s plan is missing, and
  discards it — and it pays that open even when `--frames` made the fallback
  moot, where before the container was opened only for the fallback.
- `tests/integration/test_v2_oracle.py` still derives `SPAN` from the declared
  lookahead, and its module docstring and
  `test_the_span_is_the_widest_the_footage_can_answer_for` both explain that
  derivation by "the plan does not clamp it". True of the plan the oracle builds
  and no longer true of the command it invokes: passing `--frames 0:29` and
  passing nothing now produce the same run, and the workaround has become a
  pinning of a number that the run would arrive at by itself.

Neither was covered by the criterion, which was about the shortfall being named
— a thing that now happens, in one of the three files it listed, under the other
item's spelling.

### Folded 2026-08-10: in the window the same failure is silent

10.3 met the first bullet from inside the GUI. `app._paint_viewport` renders one
frame through `PreviewSession`, so the last frames of every clip under a centred
detector raise `Frame N out of range` there too — and the viewport's answer to a
render that raised is the source frame with the `source` badge on it, which is
the same answer it gives for a node that has no picture at all. So where `sieve
preview` dies with a message, the tuning loop shows a plausible frame of footage
and says nothing about why the pipeline is not on it; `tuning.last_error` holds
the exception and no surface reads it. A test standing anywhere near the end of a
clip meets this as a wait that never ends
(`tests/gui/test_block_field.py` documents the ceiling it works within).

It changes nothing about the three candidates — the ceiling is still the missing
number — but it moves what "proven where a user meets it" reaches: whichever
answer lands, the window is a second invocation that fails today, and its failure
is quieter than the command's.

### The criterion is widened to what is left (review of f6508d7, 2026-08-08)

`-k trailing_shortfall` over `test_plan.py`, `test_executor.py` and
`test_cli_run.py` selected nothing when this review ran it, so it was not
falsely green — but it had stopped bounding anything real. A single unit case
in `test_plan.py` spelling the new field would turn it green over work that is
already committed, and `-k` cannot require a second file to contribute, so
lengthening the list does not help: whichever file answers first satisfies it.

So the criterion is now the invocation that still fails —
`tests/integration/test_cli_preview.py`, a case spelling both
`trailing_shortfall` and `preview` — for the reason the paragraph below already
gives for choosing an integration file: the answer is proven where a user meets
it. `sieve run` is proven and out of the criterion; `sieve preview` is the one
left. Still not pinned, and deliberately: whether `FrameSource` grows a length,
whether `PreviewSession` takes a ceiling argument, or whether `preview_cmd`
passes the `footage_end` it already computes.

The oracle's stale prose is not criterion-shaped and rides along with this:
`test_v2_oracle.py`'s module docstring and
`test_the_span_is_the_widest_the_footage_can_answer_for` both explain `SPAN`
by "the plan does not clamp it", and `SPAN.end` is 29 — the number `sieve run`
now derives by itself — so the sentences are false about the command even
though the arithmetic they assert still holds.

Deliberately not pinned: whether the run completes or refuses when nothing is
left, and where the number is computed. The first is the phase-5 item's
sentence — keep the refusal when the span empties — and the second is the
choice among the three. The integration file is in the command so that the
answer can be proven at the invocation that fails today rather than only at the
layer that computes it; if the answer turns out to be entirely inside
`plan.py`, the two unit files carry it and the third contributes nothing, which
costs a collection and no coverage.
