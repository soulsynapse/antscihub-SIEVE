# The stress document's walk against its floor

2026-11-21, on v5-period at `0a719e96`. The measurement is
`docs/findings/experiments/2026-11-21-the-stress-documents-walk-against-its-floor.py`, one run of
42 s on a machine not left alone, over `video-tests/GoPro-stress-test-periods.json` as Kendrick
saved it at 13:36 and the crop of `square-6` the store holds for it, 260 by 260, 11308 rows at
23.98 fps. Timings moved by a third between runs of the same script; the ratios held. Nothing of
the player was changed.

## What the document asks for

Four numbers a row, and nothing else. `region` serves the crop, and four walked nodes read it:
`changeenergy`, `motion`, `speed` below `flow`, and `changeenergy_3` below `bg-subtract` against a
`background` of 50 rows' median. A `reduce` of `mean` heads each, banded and unsmoothed, and each
gates a `period`. One frame node, `changeenergy_2`, sits below `period`, and no series node sits
below any of the four, so the plan has no timed walk: once the clip's run is held the periods are
made by one sync and no period is walked.

| `period` | periods | rows kept | of one row | median rows | longest |
| --- | --- | --- | --- | --- | --- |
| `period` | 1170 | 4913 | 394 | 2 | 69 |
| `period_2` | 1112 | 4049 | 571 | 1 | 75 |
| `period_3` | 733 | 3043 | 374 | 1 | 53 |
| `period_4` | 850 | 2460 | 302 | 2 | 21 |

That sync, with the whole clip's gates held as a run, took 10 to 20 ms for the 3865 periods.

## The ways, slowest to fastest

Each way's signals were set against the player's: equal to the last bit but `speed`'s, which
differs by under 1e-5 of a signal near 35 where `cv2.magnitude` stands in for `numpy.hypot`, and no
row's gate differs under the document's bands by any way.

| way | ms a row | the clip |
| --- | --- | --- |
| the walk under the window's memo, rows 1500 to 3000, the memo full | 6.61 | 75 s |
| the same, rows 0 to 1500, the memo filling | 3.16 | 36 s |
| the walk as `bare.py` drives it, the memo at 64 MB | 1.94 | 22 s |
| the tools' own `run()` and `fold()` in a loop, no graph, no decode | 1.41 | 16 s |
| the same arithmetic fused, one thread, no decode | 0.94 | 11 s |
| fused, a row a task over 4 threads, decode beside it | 0.57 | 7.3 s |
| fused over 16 processes, each decoding its own stretch of rows | 0.28 | 3.2 s |

Decoding the crop is 0.07 ms a row, 0.8 s the clip, and is no part of the cost.

## Where the time is

**The memo's limit.** The one walk, the one document and the one plan run three times slower once
the memo holds 4 GB than when it may hold 64 MB. A row of this document leaves about 1.4 MB of
planes in the memo: `flow`'s field, `speed`, two change energies, `motion`, `bg-subtract`. The clip
walk reads none of them again: its chain reads the four folded numbers, and a tool reads the row
before its own. Measured apart from this script over the same walk, by 500 rows: 64 MB, 1.9 to 2.0
ms throughout; 1 GB, 2.2 rising to 2.8; 2 GB, 2.2 rising to 6.0 and staying there after the memo
filled near row 1500. While the memo fills, the process takes 394 page faults a row against 29 at
64 MB, which is the planes landing on pages never touched. Why it stays slow once full is not
pinned: the faults fall to about 115 a row, and the profile shows numpy's own operations slower,
each by the same factor, and `cv2.GaussianBlur` not; the allocator handing back cold or decommitted
blocks is the likely cause and was not shown. A loop of `flow.lk` alone that keeps 2 GB of its
outputs is no slower than one that drops them, so holding memory is not by itself the cost. The
ways run after a walk under the large memo, in the same process, were slower too, `bare` 2.7 ms a
row against 1.4, which is why the script runs that walk last.

`bare.py` holds 64 MB by `HOLD` and says why. The window's worker walks the clip under the
window's own memo.

**The window, beyond the memo.** A `PlayerWindow` opened offscreen on a copy of the document with
nothing held, its clip walk asked once, reached row 5623 in 48 s: 116 rows a second, 8.6 ms a row,
against 4.8 to 6.6 for the headless walk under the same limits. The GUI thread was in Python in 1%
of 10775 samples of its stack, so it is not the window's thread taking the interpreter. The
remaining third was not found. This was a script that opens a window and polls, so it is not kept
in the tree; the number is one run's.

**The graph over its tools.** The walk at 64 MB is 1.94 ms a row and its tools alone 1.41, less
0.07 of decode: about a quarter of the walk is the graph, the memo, the probe and the stepping.

**The tools' arithmetic.** Of the 1.41 ms: `flow` 0.76, the four folds 0.22, `speed` 0.18, each
`changeenergy` 0.12, `bg-subtract` and `motion` 0.01 between them. Fused, it is 0.94, and of that
half is seven `GaussianBlur` at 67 us each. What fusing removed: `numpy.gradient` at 160 to 310 us
against two `Sobel` at 60; `numpy.hypot` at 200 against `cv2.magnitude` at 13; the `where` inside a
`where` for the inverse at 115 against a masked divide at 65; `sum(dtype=float64)` and
`count_nonzero` at 42 and 34 against `sumElems` and `countNonZero` at 4 and 12; the frame made
float once and differenced once where `changeenergy`, `motion` and `flow` each do it. Blurring four
planes as one four-channel image is slower than four blurs, 407 us against 285, and the merge and
split cost 800 more.

**Threads.** A pool of threads stops gaining at 4: 0.67, 0.49, 0.53, 0.57 and 0.60 ms a row at 2,
4, 8, 16 and 32 over 3000 rows. Processes do not stop there, 16 of them walking the clip in 3.2 s
with their own decode, after 0.6 s to start.

**The fold.** Folding the sum alone, which is all `mean` reads, takes 0.05 ms a row off the
threaded way: the max and the count are not where the fold's time is once it is `cv2`'s.

## What this does not say

Nothing here walks a period. This document gives the lanes no period to walk, so the cost of the
period walks, a walk a cut over thousands of cuts of one and two rows, is unmeasured by it; a
series node below one of the `period` nodes would make it so.
