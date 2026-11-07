# The clip walk's stack: a head without fold() cannot walk the clip

2026-10-31, on v5 over 6a53f8d9, with the clip walk as first built in `sieve_player/worker.py`.
The file is `video-tests/rep3_intermittent_crop.MP4`, 456×462 at 59.94 fps, 30579 rows; the chain
gray → motion → reduce → smooth. Figures are arithmetic from the row shape, not measurements, except
the walk time, one run offscreen.

## What the stack is

The worker hands the head's `run()` the walked node stacked over the rows, `(T, …)`, allocated whole
before the first row is written. With a `fold()` on the head, a row is what the fold returns; without
one, the plane.

| head | per row | loop window, 600 rows | clip, 30579 rows | 1080p clip, same length |
|---|---|---|---|---|
| reduce (fold: 4 float64) | 32 B | 19 KB | 1 MB | 1 MB |
| no fold, motion's plane | 211 KB | 126 MB | 6.4 GB | 63 GB |

The window works for both. The clip works only for the first: the second is a MemoryError or a
swap storm at `np.empty`, before any row, surfacing as "tool raised at row 0". The clip walk with
reduce as head covered all 30579 rows in about 20 s.

## What the guard is

`_clip_one` refuses, at the first row once `out.nbytes` is known, when `count × nbytes` exceeds
`STACK_BYTES` (`CLIP_BYTES` when this was written), and says the figure and the head's name in the header. The limit is a guess that
matched the memo's default; it enforces by bytes a rule the contract does not state.

## The rule it stands in for

Chunking the head's run and concatenating the signals would remove the stack, but only for a head
whose rows are independent. The contract gives the head the whole stack so a temporal head can see
across rows, and says nothing about which tools need that; a head normalising against the stack's
maximum answers differently per chunk. A `fold()` is already a declaration of per-row independence.
So the choice is between stating "the clip walk requires a fold" and refusing on the contract rather
than on bytes, or adding a row-independence flag to the tool contract and a chunked path behind it.
Open; Kendrick's.
