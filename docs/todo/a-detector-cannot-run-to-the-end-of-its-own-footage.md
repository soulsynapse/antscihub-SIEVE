---
title: A detector cannot run to the end of its own footage, and says so as a frame index
priority: high
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# A detector cannot run to the end of its own footage, and says so as a frame index

`sieve run` over a project holding a `detect` node, with no `--frames`, fails.
The default span is the whole video (`span_for`), the plan charges the node's
declared read-ahead past `span.end`, `decode_range` is unclamped at that end by
design, and the reader is asked for a frame past the last one:

```
arena-1: Frame 40 out of range 0..39
```

Two things are wrong with that and only one of them is the message. A user who
asked for frames 0 to 40 of a 40-frame video is told about frame 40, with
nothing naming the read-ahead, the node that declared it, or the fact that this
is the *whole video* they asked for and not a typo. And the run refuses
entirely where it could answer for every frame the footage can support — which
for the stirred clip at a 7 Hz band is 29 of 40, and for a real clip is all but
the last fraction of a second.

`pipeline/plan.py` states the asymmetry deliberately: it knows where footage
begins and cannot know where it ends, so "refuse rather than run short" is a
question for a caller that has opened a container. `cli/run_cmd.span_for` is
that caller — it opens a `VideoReader` for exactly this fallback — and does
nothing with what it learned. So the decision has a home and is not being made
there.

What "done" looks like is a decision rather than a clamp applied by reflex.
Silently narrowing the span would make a run answer for fewer frames than the
user asked for without saying so, which is the shape `_execute_one`'s
under-warmed warning already exists to avoid on the other side; the lead-in's
own answer — clamp, and report the shortfall — is the precedent, and the
symmetric one here is to narrow, name how many frames were dropped and why, and
keep the refusal for the case where nothing is left.

Filed high because it is the default invocation of the only graph shape Phase 4
built the contract for. `tests/integration/test_v2_oracle.py` works around it by
deriving its span from the declared lookahead, which is a test knowing something
no user can be expected to.
