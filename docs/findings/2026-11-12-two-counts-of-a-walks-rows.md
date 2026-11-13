# The control's count of a walk's rows and the ledger's agree on a live walk and part on a served one and on a row a scrub ran first, each time by what is counted and not by a miscount

2026-11-12, on v5-monitor over c0ec2e20 with the working tree of `docs/spec/stream-seams.md`'s deliverables
through The poll judges a walk once, by `docs/findings/experiments/2026-11-12-two-counts-of-a-walks-rows.py`,
offscreen. It is the observation of the Fork under One reading of a walk's start and of what its rows were.

For every window walk that reached its last row, two triples of rows that ran, that a store held and that
read a bake. The control's is the Worker's `walked` signal as the walk closed, which `pace.Figure` holds and
the player's header and the monitor's draw. The ledger's is `Node.ran`, `held` and `served` of the walked
node on the walk's record, which the monitor's table is made from. Twenty-nine walks: the five healthy
walks and the nine simulations of `dev/simulations.py`, and `video-tests/purb-settings.json` with its bake
live and as the document has it, baked, each over a cold walk of 300 rows, the same again, one begun 150
rows on and one scrubbed every forty rows to rows outside the window.

## Where they agree

Twenty-two walks, every one that read no bake and that no scrub reached into: cold, held, half held, under
a memo or a cache too small, slowed, held between rows. On purb live the four walks read (300, 0, 0),
(0, 300, 0), (150, 150, 0) and (300, 0, 0) by both. The scrubs to rows outside the window moved neither.

## A served walk: the control counts the row, the ledger the node

Six walks, the `unread` simulation, both of `reader`, and three of purb baked.

| walk | the control | the ledger, walked node | the ledger, the bake's node served |
|---|---|---|---|
| purb baked, cold | (0, 0, 300) | (300, 0, 0) | 300 |
| purb baked, again | (0, 300, 0) | (0, 300, 0) | none |
| purb baked, half on | (0, 150, 150) | (150, 150, 0) | 150 |
| purb baked, scrubbed | (0, 0, 300) | (300, 0, 0) | 300 |
| unread; reader, twice | (0, 0, 64) | (64, 0, 0) | 64 |

`_Walk.turn` counts a row served when a bake's file was read anywhere under it, and ran only when none was.
The ledger counts each node by itself: the walked node ran, downstream of the bake, and the bake's node is
the one served. Both are right of what they count, and the number that is the control's "served" is in the
ledger on another node's row. A reader holding the monitor's header beside its table sees a walk that is all
served above a walked node that all ran.

## A row a scrub ran first: the ledger counts a fold as the node running

One walk, the `scrub` simulation, which asks for row 56 as the walk passes row 8: the control (63, 1, 0),
the ledger (64, 0, 0). The scrub's turn ran video, gray, work, bake and edge at row 56 in its own lane. When
the walk reached the row its `walk_row` found edge in the memo, so the control's tally saw no miss and the
row is held. The walk then folded the densities of gray, work, bake and edge at that row, the scrub having
folded none, and `ledger._RAN` holds "fold": a row on which only a node's fold ran is that node's `ran`. On
the same record video reads (62, 1, 0), which is the row the scrub decoded.

## What it does not show

No walk was scrubbed inside its window on purb, where the scrubs were aimed outside it; the one row is the
simulation's. The clip lane was not compared. Where a walk begins, the other half of the section's title,
`ledger.Walk` opening at "begin" and `pace._Walk` at a count that does not rise, was not observed: every walk
here was matched by its closing signal, and a walk restarted before its first row is in neither count.
