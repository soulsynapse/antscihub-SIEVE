# A progress signal at every row is a quarter of a short row's walk in the player

2026-11-13, on v5-crop2 over 80462761 with `tools/detect.py` and the catalogue's `signals` class in the
working tree, on an i9-14900KF, by `docs/findings/experiments/2026-11-13-a-signal-a-row.py`, offscreen
under Qt's own event loop. Kendrick was using the player on the same machine throughout, so every figure
is against its neighbour of the same minute and none is the machine's best. The clip and the document
are those of `docs/findings/2026-11-13-detect-on-a-thresholded-crop.md`: `square-1.mp4`, 256 by 256,
video as luma, threshold at 163, detect with `dark`. Kendrick read about 900 rows a second off the
player on this document, where that finding has the bare walk at 4700 to 5900.

## The clip walk in a PlayerWindow, one thing changed at a time

Six seconds of the clip walk, each word alone in a process, by turns:

| | rows a second | ms a row |
|---|---|---|
| the player as it is | 1346, 1330 | 0.743, 0.752 |
| `worker._Walk.report` emitting at one row in 30 and at the range's end | 1766, 1814 | 0.566, 0.551 |
| that, the window never shown | 1935 | 0.517 |
| that, nothing listening to the stream: no ledger | 2153 | 0.464 |

On the first 30000 rows cut to a file of their own, five seconds each, earlier the same hour: as it is
1638 and 1508 rows a second, reporting at one row in 30 2181 and 2272, hidden 2382 and 2419, no stream
2510 and 2365.

The walk reports its progress at every row, `clipWalked` on the clip's lane and `walked` on the
window's, and the window's slot on it runs on the GUI thread once a row. The slot's own spans were 0.034
ms a row. What the walk lost to it was 0.18 to 0.19: the ledger's figures for the nodes fell with it,
the decode from 0.27 to 0.21 ms a row, detect from 0.20 to 0.14 and the unprobed from 0.07 to 0.035,
none of which the slot ran in. A tool here makes some eight OpenCV calls a row of a few microseconds
each and lets go of the interpreter at every one; a GUI thread woken once a row takes it at one of them
and the worker waits to have it back.

## What the catalogue said

Of the walk as it is, `waits` named the clipWalked slot at 0.06 ms a row, a third of what removing it
gave back, and nothing named how often it ran. `signals`, entered the same day, is a slot run at one row
in two or oftener, under a millisecond a call, its own spans 4% or more of the walk's cost: it named the
slot at 0.034 ms a row on both runs of the walk as it is and on neither with the report at one row in
30. Its figure is the slot's own spans and so the floor; the rest is in the tools' spans, as above.
`Bucket.calls` counts a GUI span where it began, which the class reads.

## The bare walk at the player's settings

`Graph.walk_row` over 12000 rows of the 30000-row cut, no worker, by OpenCV's threads and what the memo
and the decoder's cache may each hold, one run and the first and last cases again:

| | ms a row | rows a second |
|---|---|---|
| 1 thread, 16 MB | 0.149, 0.185 | 6691, 5405 |
| 32 threads, 16 MB | 0.182 | 5506 |
| 1 thread, 4 GB | 0.224 | 4469 |
| 32 threads, 4 GB | 0.217, 0.218 | 4606, 4583 |

The player's own settings, 32 threads and 4 GB, are the last row: 0.22 ms. The stores at 4 GB are 0.04
to 0.07 of it, as `docs/findings/2026-11-13-sieve-against-the-trex-port.md` on v5-runs found on another
clip; OpenCV's threads did not separate from the runs' own spread.

## What it does not show

The window was offscreen and its harness's, not Kendrick's on a screen with the monitor open, where he
read 900. With the report thinned and no ledger the player's row is still twice the bare walk's, 0.46
against 0.22, and that half was not split: the worker's turn outside `walk_row`, the stream's events
with nothing listening, and the GUI thread's timers are in it. The window lane signals `walked` into
three slots a row and folds each frame node's density besides, 0.10 ms a row for the threshold's plane
by the ledger; the window walk was timed only under a harness that spun the event loop, 697 and 803 rows
a second over 20000 and 6000 rows, and those are not figures of the player. `plot.Field.crop` reads
every row of the window's densities at each `walked`, so the window walk's row grows with the window;
that was seen in a profile and not measured. No change to `worker._Walk.report` was made: what the
progress bar and the pace read of a slow walk at one row in 30 is the player's to decide.
