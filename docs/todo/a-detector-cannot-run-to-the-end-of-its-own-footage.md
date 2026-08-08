---
title: A detector cannot run to the end of its own footage, and says so as a frame index
priority: high
phase: 5
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/integration/test_cli_run.py -q -k end_of_footage"
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

The general form of the question — who answers for a window that runs off the
end, given `plan.py` cannot open a container — is
[the-trailing-end-of-a-window-has-no-shortfall.md](the-trailing-end-of-a-window-has-no-shortfall.md),
which enumerates three candidates. The reading proposed above is that item's
first candidate, and this item is the failure that prices it rather than a
second decision about the same thing.

Both files say that one drains first, on the strength of its being phase 3. It
is phase 8 now, so the order has inverted: this item reaches the head of the
queue first, and the session that takes it makes the choice among the three
rather than inheriting it.

## The criterion pins the invocation, not the layer that answers it

Two cases spelling `end_of_footage` in
`tests/integration/test_cli_run.py`, which is the file that already holds both
halves of "the flag or the whole video" — and both halves of this item are only
visible where a user types it. One is the default invocation over a graph with a
declared read-ahead: it must complete, and what it prints must name how many
frames it could not answer for and the node whose read-ahead cost them. A
message-only fix is refused by that as firmly as the `Frame 40 out of range
0..39` it replaces, because the run still answers for nothing; so is a silent
narrowing, which prints the count of frames it did run and nothing about the
ones it dropped. The other is the span short enough that nothing survives the
read-ahead, which still refuses — the sentence above about keeping the refusal
is the clause the trailing item's criterion deliberately left to this one.

Not pinned: where the number is computed. `span_for` is named above as the
caller that has a container open and is still the argument, but a plan handed a
ceiling some other way that prints the same sentence passes this. That is the
choice among the three candidates, and it stays with the work.
