---
title: swipe
group: Layer 1
position: 6
gloss: A run of views laid side by side in one pane, one in front at a time, reached by sliding the run rather than by replacing what the pane holds. A swipe is itself a view.
origin: decided
defined: 2026-08-10
---

A run of [views](view.md) laid side by side inside one [pane](pane.md), one of
them in front at a time, reached by sliding the run rather than by replacing
what the pane holds. A swipe is itself a view: it occupies one pane and never
adds one, so a screen reached by swiping is a position on the track and not a
pane of its own. "Pane" is not a synonym even though the mockup's names use it:
panes are countable and fixed, and a construct that grew two more each time a
screen was added would make "which pane" unanswerable.

The word covers the track and every position on it. The right pane's swipe is
the three: the project, the pipeline, the step. Their order is the reading
order of the work, which is what lets ← and → mean out and in without a label
saying so.

## Where it lives

`gui/frame/swipe.py`. The positions sit on a track wider than the pane and the
track slides, so the direction of travel communicates position; the track
moves, never the positions.
