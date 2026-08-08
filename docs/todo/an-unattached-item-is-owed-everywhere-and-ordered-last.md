---
title: An unattached item is owed everywhere and ordered last
priority: high
status: open
gated_on: nothing
opened: 2026-08-07
---

# An unattached item is owed everywhere and ordered last

Two comments in `doc_index.py` reason from the same premise to opposite
orderings. `owed_pool`: "Unattached items are owed at every boundary: repo-wide
work belongs to no phase, so no later boundary is more its own than this one."
`_pool_order`: "Unattached last: a pool item with no phase is repo-wide, so it
has no place among the phases." If no later boundary is more its own, then this
one is as much its own as any — which is an argument for sorting among the
phases, not behind them.

The effect is measurable and currently upside down. Five items carry no phase,
all of them loop machinery, two at `high` — `a-run-commits-what-it-wrote` and
`minting-an-item-cannot-overwrite-one`. Both sort behind all seven of phase 0's
`low` items, so the drain runs `the-gate-does-not-check-formatting` before a
guard against silently deleting an item.

What forced the question is the rule that a phase *is* the priority: pool items
attach to phases, the phase orders the drain, and `priority` breaks ties inside
one. That is what `_pool_order` already implements and it is right for anything
with a phase. It leaves an unattached item with no position at all, because the
reading where `priority` carried it is exactly the reading the rule removes.

Three answers and the item is the choice.

- Sort unattached first, by priority. Follows `owed_pool`'s premise literally
  and matches "owed at every boundary": if it is owed here as much as anywhere,
  here is where it runs.
- Make `phase:` required on pool items and delete the unattached case. Loop
  machinery would then have to claim a phase, which is either honest — the loop
  is Phase 0's enforcement grown up — or a fiction that puts SIEVE phases on
  work that has nothing to do with the video.
- Give the loop a phase of its own outside the plan's numbering. Keeps the two
  audiences apart, at the cost of a number `PLAN.md` does not define and
  `phase_titles` cannot label.

Whichever lands, one of the two comments is deleted rather than reworded: they
cannot both stand, and the surviving one is the reason the sort is what it is.

Not settled here because it reorders the drain that is about to fire — the
lowest open step is now 05.9, and once Phase 5 and 6 close, `owed_pool(None)`
brings all forty-nine owed items due at once in whatever order this decides.

## The contradiction went; the choice did not (2026-08-07)

`owed_pool` and `_pool_order` no longer exist. `queue_key` replaced both — its
docstring records what it replaced and why — and the two comments above went
with them, so the half of this item that was "two comments cannot both stand"
is closed. What survives is the arbitrary constant they left behind:

    UNPHASED = 1 << 16

and its own comment now cites this item as the open question, saying the value
is "chosen rather than derived" and that repo-wide work being owed everywhere
"is as good an argument for first as for last". So the three answers below are
still the three answers; nothing about them turns on the old comments. What
changed is that the effect is no longer upside down by accident — it is upside
down on purpose, pending this.

The counts in the paragraph above have moved and are not worth re-pinning: two
of the five named items are `done` (`minting-an-item-cannot-overwrite-one`, and
`claude-md-says-there-is-no-code-yet`, closed on a criterion that had gone green
under some other work), leaving four unattached and two of those at `high`. The
shape is what matters and it holds — an unphased `high` sorts behind every
phase-7 `low`.

**The second answer has a doc half nothing else covers.** `PLAN.md` says "Work
is chunked into `docs/todo/` items attached to these phases", which is the
premise the whole ordering rests on and is false of four items today. If
`phase:` becomes required, that sentence is already right and the loop
machinery has to claim a phase. If unattached items stay legal, that sentence
is what has to change — and it is `PLAN.md`, so it is proposed to Kendrick
rather than written past him. Either way the sentence and the sort are one
decision and should not be made in two sessions.
