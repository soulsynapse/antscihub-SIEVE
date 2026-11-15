# The memo holds no view: every array a store counts is that store's own

Read with `sieve_player/graph.py`, whose `_compute` memoizes what a tool's run hands out and whose
`Memo` counts it by `nbytes`; with `sieve_player/decoder.py`, whose cache holds the frames a read
hands a run; and with `tools/region.py` and `tools/rescale.py`, the two tools known to hand on
their input's buffer.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

Words. A result is a *view* when it shares its buffer with an array a read handed the run that made
it, the whole of it or a part.

## Why

A region with no shape chosen hands out `np.ascontiguousarray` of the whole frame, which numpy
answers with the frame itself, and a rescale at 1.0 returns its input. The memo holds each under the
node's own key at the frame's full size, so a store counts bytes the video cache already holds: a
monitor report read SIEVE at 5.9 GB with a memo and a video cache of 4.0 GB each, and the window's
need of the memo at three planes a row where one was the memo's own. The memo then discards for room
it is not short of, and what it discards of a view frees nothing.

A strip the plate's width is a view too, counted at the strip's size while it keeps the whole frame
resident after the cache lets it go: bytes no store counts, under limits that then bound nothing.

## The memo holds no view

Assumes: nothing.

- [ ] No plane the memo holds shares memory with an array a decoder's cache holds, the plate's or a
  served file's, nor with another plane of the memo's own: a result that is a view is held as a copy
  of its own, whatever tool made it. A result that is no view is held as it was made, uncopied.
  Check: `tests/test_graph.py`, an invariant: a tool that returns its input, one that returns a
  strip of it and one that returns a new array are each walked, and `np.shares_memory` is read
  between what the memo holds and what the cache does.

## What the copies cost

Assumes: The memo holds no view.

- [ ] A finding holds, for the report's plan walked before and after: the ms a row of region and of
  rescale, the window's need of the memo, the stores listed under MACHINE against SIEVE's memory,
  and how many rows of a window's history the memo keeps.
  Check: a one-off under `docs/findings/experiments/`, the finding beside it.

## Not here

A node that hands on its input unchanged still runs and its result is held, as a copy:
docs/spec/pass-through.md holds the plan leaving such a node out, and reads this spec's finding for
whether that is worth its facet. One count of a shared buffer across the stores, with one limit over
the memo and the caches. Arrays behind a table's object column.
