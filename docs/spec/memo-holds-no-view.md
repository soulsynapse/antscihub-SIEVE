# The memo holds no view: every array a store counts is that store's own

Read with `sieve_player/graph.py`, whose `_compute` memoizes what a tool's run hands out, whose
`Memo` counts it by `nbytes` and whose `peek` the window paints from; with
`sieve_player/decoder.py`, whose cache holds the frames a read hands a run; and with
`tools/region.py` and `tools/rescale.py`, the two tools known to hand on their input's buffer.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

Words. An array is *a store's* when a decoder's cache or the memo holds it. A result *is* a store's
array when it is the very array a read handed the run, whole. A result is *part of* a buffer when it
shares memory with an array larger than itself, a store's or one the run made. A *reference* is what
the memo holds in place of an array: the key of the node that was read and the row it was read at.

## Why

A region with no shape chosen hands out `np.ascontiguousarray` of the whole frame, which numpy
answers with the frame itself, and a rescale at 1.0 returns its input. The memo holds each under the
node's own key at the frame's full size, so a store counts bytes the video cache already holds: a
monitor report read SIEVE at 5.9 GB with a memo and a video cache of 4.0 GB each, and the window's
need of the memo at three planes a row where one was the memo's own. The memo then discards for room
it is not short of, and what it discards of a view frees nothing.

A strip the plate's width is a view too, counted at the strip's size while it keeps the whole frame
resident after the cache lets it go: bytes no store counts, under limits that then bound nothing.

A copy of every such result makes the count true by making the bytes real: the report's walk then
takes the sum of the two limits and a frame's copy a row, to hold a plane the cache has. A bypassed
Houdini SOP hands on its input's detail handle and Blender's geometry shares an array among its
users, each counted once and each mutable only by a sole user. Here one store holds the array, the
memo names it, and nothing writes to it.

An array shared is safe only while nothing writes to it, and nothing says so now: a tool that draws
on the frame it was handed rewrites the cache's frame for every other reader, silently.

## What a read hands is read-only

Assumes: nothing.

Facts to weigh. cv2 refuses a read-only array as the array it writes into, so such a tool raises
where it wrote. No tool is known to write into its input, by a search and not by an audit.

- [ ] Every array a read hands a run, and every array `peek` hands the window, is read-only, as is
  every array the memo holds: a tool that writes into its input raises, and the node says so as it
  does of any raise.
  Check: `tests/test_graph.py`, an invariant: a tool that writes into what `frames(row)` handed it
  raises, and the cache's frame is as it was.

## The memo holds no view

Assumes: What a read hands is read-only.

Facts to weigh. A node read under a band is handed `np.where`'s array, which no store holds, so a
result that is that array is the memo's own. `peek` reads the memo or a cache by the entry's kind
and runs nothing. A static node's result is pinned and outlives every walk, where a cache's frame
goes when the cache needs the room.

- [ ] A result that is a store's array is held as a reference and no array, and the memo counts no
  plane for it. A read of the node at that row, and `peek`, answer the array the store holds,
  through as many references as lie between, under the node's own band; where the store has let the
  array go, the read runs the node again and `peek` answers nothing. The tool has run for the
  reference to be made, so what it raises of its input it still raises.
- [ ] A result that is part of a buffer is held as a copy of its own, so the memo keeps resident no
  byte it does not count.
- [ ] A result that shares no buffer is held as it was made, uncopied. A pinned result is an array
  of the memo's own, never a reference.
  Check: `tests/test_graph.py`, an invariant: a tool that returns its input, one that returns a
  strip of it, one that returns a strip of an array it made and one that returns a new array are
  each walked. `np.shares_memory` between any array the memo holds and any the cache holds is
  false, no array the memo holds has a base larger than itself, the first tool's result is the
  cache's array by `compute` and by `peek`, and with the cache emptied its read decodes the row
  again.

## What it costs

Assumes: The memo holds no view.

- [ ] A finding holds, for the report's plan walked before and after: the ms a row of region and of
  rescale, the window's need of the memo, the stores listed under MACHINE against SIEVE's memory,
  and how many rows of a window's history the memo keeps.
  Check: a one-off under `docs/findings/experiments/`, the finding beside it.

## Not here

A node that hands on its input unchanged still runs, and has a key of its own: docs/spec/pass-through.md
holds the plan leaving such a node out. One limit over the memo and the caches. Arrays behind a
table's object column. What a walk's stack and the held runs hold.
