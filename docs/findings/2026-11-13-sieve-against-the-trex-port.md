# SIEVE's tools already cost what the TRex port's do; the walk around them is where the rows a second go

2026-11-13, on v5-runs at 7bc71e00 with an i9-14900KF, by
`docs/findings/experiments/2026-11-13-sieve-against-the-trex-port.py`, offscreen, one OpenCV thread, every
word row-limited. The clip is `video-tests/03c2012ed6e61417.mp4`, 234 by 304 and 38100 rows, through
`video-tests/bg-subtract-compare.json`. The port is the Python reproduction of TRex 1.1.9 kept outside the
repo at `Code/Scratch/trex119-baseline/trex119.py`, whose pv and tracks are TRex's own to the pixel; its
figures here are of the same night: conversion at 3043 frames a second with one worker thread and about
3700 with eight, 85 MB written, and tracking in 3.0 s. TGrabs 1.1.9 itself, `-nowindow`, took about 34 s
on its one run, and TRex about 10 s to track with posture, about 3 without.

## A row, step by step, on held rows

ms a row over 6000 rows, least of three, at the port's settings, a threshold of 60 and regions of 137
pixels and up, one record a row:

| step | ms |
|---|---|
| the Decoder's luma read | 0.104 |
| cv2's read to BGR and one channel taken, as the port and TGrabs do | 0.094 |
| absdiff, threshold | 0.005 each |
| `blobs.find` | 0.223 |
| `runs.find` | 0.134 |
| the port's labeling: `connectedComponentsWithStats`, then runs cut inside each kept box | 0.161 |
| `connectedComponentsWithStats` alone | 0.147 |

Decode, difference, threshold and `runs.find` are 0.25 ms, four thousand rows a second, and `runs.find` is
under OpenCV's labeling alone. `track.link` over the 6000 tables took 0.054 ms a row, 18600 rows a second.

## The walk, on one thread

`Graph.walk_row` over 8000 rows, nothing attached, a fresh graph each, two runs, before the two changes
named further down:

| | ms a row | rows a second |
|---|---|---|
| the document as it is: threshold 31, min_area 50, blobs with a contour, 2.45 records a row | 0.585, 0.595 | 1709, 1679 |
| threshold 60, min_area 137, 1.19 records a row | 0.493, 0.478 | 2030, 2092 |
| the same, runs in place of blobs | 0.407, 0.414 | 2457, 2413 |
| the same, the memo and the decoder cache held to 16 MB each | 0.351, 0.348 | 2849, 2875 |

The last row is within a tenth of the port on one thread. Between it and the row above is every plane of
every node kept, 213 KB of new memory a row, against planes dropped a few rows after they are made. The
worker's clip walk of the whole clip under a ledger, alone in a process, read 1631 and 1652 rows a second
against the bare walk's 1961 on the same document.

## Through a thread pool

Difference, threshold and a labeling over 4000 held rows, rows a second at 1, 2, 4 and 8 pool threads,
two runs:

| | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| `blobs.find` | 3880, 3353 | 6349, 5258 | 5626, 4599 | 5645, 4330 |
| `runs.find` | 5069, 4253 | 4257, 3263 | 3920, 2932 | 3547, 3430 |
| the port's label and crop | 5058, 5002 | 8381, 7863 | 11809, 11062 | 11155, 11018 |

`runs.find` is slower on any second thread: it is many small numpy calls and holds the interpreter between
them. The port's labeling is one OpenCV call and a few numpy calls a kept region and passes the decode,
which at 0.104 ms is some 9600 rows a second, at four threads.

## The same calls with no graph around them

`Decoder.read`, `bg_subtract.difference`, `cv2.threshold` and a labeling over 12000 rows, the decoder's
cache at 16 MB and nothing kept but the tables, the frames handed 32 at a time to the tool threads where
there are any; rows a second, two runs:

| | the reading thread alone | 1 tool thread | 2 | 4 |
|---|---|---|---|---|
| `runs.find` | 4250, 4209 | 3980, 4013 | | |
| `blobs.find` | | 3859, 3580 | 4127, 4509 | |
| the port's label and crop | | 5154, 5218 | 6446, 8126 | 7338, 7383 |

One thread calling the player's own decoder and tools in a loop is past the port's eight. A second thread
does nothing for `runs.find` and takes the port's labeling to five thousand, and two more to seven.

## What the graph adds, and what a kept plane costs

The same day, after two changes that alter no result: `_table.plane_dtype` kept by shape, where it built a
dtype of fourteen fields at every row, and `Memo.put` handed the size `_compute` had already counted. The
walk of the third case above, 6000 rows, by what the memo and the decoder cache may each hold, three runs,
the decoder's cache emptied after row 0 in the last:

| held, each | ms a row | rows a second |
|---|---|---|
| 1 MB | 0.266, 0.268, 0.273 | 3763, 3736, 3668 |
| 4 MB | 0.326, 0.293, 0.282 | 3065, 3415, 3547 |
| 16 MB | 0.316, 0.298, 0.277 | 3168, 3360, 3615 |
| 256 MB | 0.320, 0.326, 0.296 | 3122, 3071, 3378 |
| 16 MB, a ledger attached | 0.343, 0.359, 0.336 | 2914, 2786, 2974 |

The whole graph, memo, probes and Frames with it, is 0.03 to 0.09 ms a row over the plain loop, and on one
thread is between the port's one and its eight. The runs differ among themselves by as much as the sizes
from 4 MB up do, so what those say is only that 1 MB is the quickest and 256 MB the slowest by about a
tenth. A ledger is 0.04 to 0.06 ms. The larger cost is before a store first fills: the walk's table above
has 0.41 ms a row with 4 GB stores over 8000 rows against 0.35 at 16 MB, every plane written to pages
never touched, and the full clip's bare walk at 1961 rows a second against 1700 over its first 8000 rows
is the stores filling.

## The same on larger frames

The same chain on two larger clips, each store at so many rows of the chain's four planes, two runs, the
decoder's cache emptied after row 0:

| ms a row | 8 rows | 64 rows | 1024 rows |
|---|---|---|---|
| `rep3_intermittent_crop.MP4`, 462 by 456, a plane 205 KB, 3000 rows | 0.423, 0.446 | 0.448, 0.421 | 0.499, 0.506 |
| `00000_168-178.mp4`, 1920 by 1080, a plane 2 MB, 590 rows | 3.59, 4.08 | 3.57, 3.62 | 3.40, 3.34 |

Keeping few planes is a seventh quicker at 205 KB and a twentieth to a fifth slower at 2 MB, where the
store of a thousand rows never filled in 590 and discarded nothing. A first run of this table, without
the cache emptied, had the 1080p walk 1.7 times slower when it discards: the background's fifty samples,
read at row 0, step through every frame of a 590-row clip, so with room to keep them the walk decoded
nothing. That figure was the decode and is withdrawn.

What an array of a plane's size costs with no graph near it, us each, two runs agreeing:

| | made and kept | freed | made and dropped at once | made into a ring of 8 | one buffer written again |
|---|---|---|---|---|---|
| 71 KB | 23 | 5 | 3 | 2 | 1 |
| 205 KB | 49 | 13 | 5 | 3 | 3 |
| 480 KB | 93 | 26 | 10 | 10 | 5 |
| 600 KB | 112 | 32 | 11 | 12 | 6 |
| 2025 KB | 331 | 54 | 362 | 382 | 25 |

Up to 600 KB a dropped array's memory is handed straight to the next and costs a tenth of memory never
touched; at 2 MB it is not, and an array costs 330 to 380 us whether the last was kept or dropped, against
25 written into a buffer already held. Where between 600 KB and 2 MB the turn is was not looked for.

`cv2.VideoCapture.read` given an array of the frame's shape decodes into it. Over 560 rows of the 1080p
clip through a ring of 32, two runs: the luma plane 1.01 and 0.99 ms a row into new arrays, 0.82 and 0.83
into the ring's; BGR 2.47 and 2.38 against 1.76 and 1.72. On the 234 by 304 clip the two are the same,
0.064 to 0.076. The 1080p walk's row under a profile was the labeling 1.5 ms, the decode 1.0, the
difference 0.4 and the threshold 0.3.

## Through the worker, and with the three nodes as one

The worker's clip walk of the whole clip under a ledger, each alone in a process, after the two changes:

| | rows a second | ms a row |
|---|---|---|
| the document as it is | 1781 | 0.562 |
| threshold 60, min_area 137, runs in place of blobs | 2359, 2343, 2238 | 0.424 to 0.447 |
| the same with `tools/segment.py` in place of bg-subtract, threshold and runs | 2660, 2667 | 0.376, 0.375 |

`segment` is the three in one run, written the same day over runs' labeling moved to `tools/_runs.py`; its
tables were the three nodes' on each of 2006 rows spread over the clip. Under the ledger its row is the
decode 0.095 ms, its own span 0.221 and 0.054 no span covers. Bare, interleaved with the three nodes over
6000 rows, three runs each: 0.300 to 0.327 ms a row against 0.321 to 0.377, and with a ledger attached
0.315 to 0.322 against 0.354 to 0.395.

Over 16000 rows of the worker's walk at the second row's settings, each alone in a process, two runs: a
Python slot on `clipWalked` or none made no difference, 2377 and 2368 rows a second against 2392 and
2409, and without a ledger 2774 and 2803. A profile of the walk's turn driven on one thread has the
ledger's fold, the progress event's facts and the signal's emit as the larger things outside a node, none
over a tenth of the row.

## The decode on a thread of its own

`Decoder.read` on one thread into a queue of 64 and `segment.regions` on the caller, no graph, 12000 rows,
rows a second, two runs of the script:

| GIL switch interval | the decode in line | on its own thread |
|---|---|---|
| 5 ms, Python's own | 4031, 3683, 3741, 3415 | 4436, 4846 |
| 0.5 ms | | 5735, 5341, 5366, 5531 |
| 0.05 ms | | 5389, 5566 |

At Python's interval the reading thread waits on the labeling for the interpreter between frames; at a
tenth of it the two overlap and the row is the labeling's.

## The clip walk with the decoder reading ahead

Built the same day: `Decoder.ahead` starts a thread that decodes on the walk's cursor into the cache, up
to 64 rows past the last row read in step, and the clip walk starts it at its first row and rests it at
its last or when halted; the interpreter's switch interval is 0.5 ms between the two and Python's own
outside them. The worker's clip walk of the whole clip under a ledger, each alone in a process, by the
experiment's `clip` words:

| | the decode in line | read ahead |
|---|---|---|
| the document as it is | 1713 | 1912 |
| threshold 60, min_area 137, runs in place of blobs | 2204 | 2825 |
| `segment` in place of the three | 2650, 2620 | 3426, 3442 |

The video node's span falls from 0.096 to 0.098 ms a row to 0.008, and the row from 0.377 and 0.382 to
0.292 and 0.291: the whole of the decode is off the walking thread and nothing else moved. The document
as it is gains least, its labeling with contours holding the interpreter less.

What the ledger then says of a row: a row the thread decoded is a "decode" of the read that first takes
it, as before, with the span the few microseconds the read took, and the decode's own time in no span.
`decodes` counts those rows as they are taken and `ahead_decodes` what the thread decoded; the cache's
discards made on the thread are told to `on_evict` by the next read, on the reading thread's caller. By
`frames`, 6000 rows read with the thread on, some reads a row back and some 3000 ahead, against a second
decoder in line: no frame differed with the cache at 4 GB or at 1 MB, where it holds fourteen frames and
the thread keeps twelve ahead; decodes 6006 and 6032 against 6012 and 6018, seeks 6 with the thread's 6
and 11 with its 6 against 12.

## The 713 rows a second of 2026-11-12 was the experiment's

`docs/findings/2026-11-12-bg-subtract-against-tgrabs.md` has the clip walk at 568 to 689 rows a second and
a bare walk falling from 1876 to 645 later in a process. Each word alone in a process: the clip walk 1631
and 1652, with the collector off or on; a bare walk 1961; a bare walk on a second thread 1789. Two bare
walks in one process read 1912 then 775, and with `gc.disable()` 1944 then 1791, resident memory then 13.8
GB against 6.9. Over two walks of 12000 rows with the collector timed through `gc.callbacks`, the second
walk spent 2.6 s of its 9.9 in one collection of the oldest generation, and the first none: the graph the
walk before left behind, which only the collector can free, a Graph and its memo's `on_evict` holding each
other. The player keeps one graph for a document, so the slow walk is not shown to be the player's.

## What it does not show

No walk of the graph's tools was run across threads: the pool figures are of held rows, and the one
thread beside the walk is the decoder's. The reading thread was not run on a clip of larger frames, nor
beside a window walk or a scrub taking the cursor from it, nor in the player with its window up, where
the shorter switch interval is the GUI thread's as well. What
the worker adds over the bare walk, a sixth on this document, was not split into its parts. Whether the
time inside the collection is the traverse or the freeing of the planes was not separated, nor whether
opening a second document in the player pays it. The memo held small is a graph nothing displays or
counts densities from; what the player needs kept was not looked at. One clip, small frames, one or two
records a row: the 2026-11-01 finding has a 960 by 540 clip where the labeling is most of a row.
