---
title: The review has a path for a partial deferral
priority: normal
status: open
gated_on: nothing
opened: 2026-08-07
---

# The review has a path for a partial deferral

The review's deferral branch says amend the criterion and set the item back
to `open`, which assumes the amendment leaves work to do. 01.2 committed
everything except the struck part, so the amended criterion passed the moment
it was written and `open` meant a session would be started to do nothing
(`findings/loop/2026.08.07-the-review-prompt-has-no-path-for-a-partial-deferral.md`).

The missing case is: the criterion was wrong, the work under the surviving
half is done, and what the strike removed is now somebody else's item. That
is `done` plus a minted item, not `open` — and the minted item is what keeps
the struck subject from vanishing, which is how 02.1's format-contract split
was handled by hand.

02.1's review found the same gap from the other side: it could settle one of
three blockers and not the other two, and had no status meaning "partly
settled, still stopped". It wrote a section in the item instead, which worked
because a human read it.

## The state itself is now detectable, whatever produced it (2026-08-08)

The three cases above all end in the same observable: an `open` item whose
`done_when` already passes, served to a work run with nothing to do. It has
since happened twice from a fourth cause — a worker that finished an item and
left `status: open` instead of `awaiting-review`
(`findings/loop/2026.08.07-a-worker-on-a-reopened-item-leaves-the-status-the-review-set.md`
and its 2026-08-08 amendment) — and the second time it cost a full work run,
because the review that had already noticed and already swept the criterion
wrote the instruction into a queue entry rather than into `status`.

So the remedy generalises past the deferral branch that opened this item.
`--next` can run the selected item's `done_when` before answering and refuse to
call it `work` when it is green, which catches every cause including ones
nobody has thought of, and is the one check that does not need to know why the
item is in that state. Two costs to weigh rather than assume: a criterion is an
arbitrary shell command and running it on every selection is not free — the
sweeps in the Phase 7 items take minutes — and a criterion that is green
because the tree is broken elsewhere would be misread as finished. The cheaper
variant is to run it only when the answer would be `work` and to report the
green rather than suppress the item, which leaves the judgement with whoever
reads it.
