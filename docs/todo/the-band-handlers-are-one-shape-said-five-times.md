---
title: The band handlers are one shape said five times
status: deferred
opened: 2026-08-05T18:08:08-07:00
priority: normal
gated_on: >
  detector-state-dies landing, which is what decides whether there are still
  five shapes to collapse
reads:
  - src/sieve/gui/filter_tab.py
  - src/sieve/gui/commands.py
after: [detector-state-dies]
---

# The band handlers are one shape said five times

`filter-tab-is-eleven-jobs`' third slice, split out so the item that holds the
plan stops carrying a slice nobody can take yet.

Five controls in `filter_tab.py` — the frequency band, the value band, the
count threshold, the D window, and solo — each spell the same two-tier drag
discipline: a cheap local repaint while the pointer is down (`_cheap_retune`
and its per-control wrappers), a full document-committed derive on release.
The repetition is not quite duplication, which is why a mechanical dedup here
would be wrong: the frequency band has an echo-compares-equal case, D carries a
gesture token, and solo is exempt from `recompute` entirely.
`filter-tab-many-secrets` records this as its second secret.

**Why not now.** `detector-state-dies` deletes `reuse_band_power` — the
one-boolean hand-rolled cache the cheap tier is built on — and says the
cheap/expensive shape survives as cache behaviour of the detection filter's
stages, which is where it belonged. That changes what the five handlers are
made of, and possibly how many of them are left: detector edits become node
param edits through the existing `EditTuningParams` path, and the drag-merge
undo mechanics that make the tiers work already live in `commands.py`. Taking
this item first would factor a shape that is about to be rebuilt from
underneath, and the result would have to be re-read against the new one
anyway. The honest form of that argument is that nobody yet knows whether the
answer is one helper, a per-control policy object, or nothing at all because
the tiers dissolved.

**The first step when it opens** is to re-count: how many of the five still
have a hand-written cheap tier after `detector-state-dies`, and whether the
three exceptions above are still exceptions. If the answer is fewer than three
controls, close this rather than build the abstraction — a shape said twice is
not a shape.
