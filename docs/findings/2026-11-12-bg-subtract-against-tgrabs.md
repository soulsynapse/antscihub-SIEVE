# bg-subtract-compare walked bare is within a factor of two of TGrabs 1.1.9, and neither figure held still

2026-11-12, on v5 at 2ded1da6 with an i9-14900KF under Windows' Balanced scheme, by
`docs/findings/experiments/2026-11-12-bg-subtract-against-tgrabs.py`, offscreen. The document is
`video-tests/bg-subtract-compare.json`: video, a median background of 50 samples, bg-subtract, threshold at
31, blobs of at least 50 pixels, on `03c2012ed6e61417.mp4`, 234 by 304 and 38100 rows. TGrabs is the conda
env `track119`'s, given the same threshold, size filter and sample count, `averaging_method mode` since it
has no median, and `-nowindow`; it wrote a pv of 100 MB and the document's walk wrote nothing.

## The figures, with nothing else of Kendrick's open

| | rows a second | cores busy, this process and everything else |
|---|---|---|
| `Graph.walk_row` at every row, nothing attached | 1360, 1099 | 16.4 and 5.5, 13.3 and 4.8 |
| the same with `cv2.setNumThreads(1)` | 1876, and 645 later in the same process | 1.5 and 3.3, 1.2 and 2.8 |
| the worker's clip walk under a ledger | 568; 689 with one OpenCV thread | 7.1 and 4.0; 1.2 and 3.3 |
| TGrabs, the whole process | 25.0 s, 36.7 s, 29.9 s | 0 and 7.8, 0 and 8.4 for the last two |

TGrabs' own line a second read 654 to 2993 fps within one run, its median 706 and 978 in the last two
runs; the first run, mostly at 2100 to 2900, converted the clip in about 21.5 s, some 1770 rows a second.
Kendrick's own runs of it read about 1800.

In the clip walk blobs was 1.16 to 1.70 ms of 1.45 to 2.23 ms a row, the decode 0.15 to 0.25, bg-subtract
and threshold under 0.2 together, and the background 25 ms once.

## What moved the figures

Runs made while Kendrick's own TGrabs and the player were open read 410 to 483 rows a second bare and are
not in the table; the experiment then had no machine sample beside its figures and has one now.

The bare loop is one Python thread and kept 12 to 16 cores busy, which with OpenCV held to one thread fell
to 1.5: OpenCV's pool, on a plane of 71 thousand pixels.

A bare walk later in a process was slower than the first in it under the same settings, 645 against 1876.
Whether that is the collector over a heap of contour objects was being tested when the session was stopped,
and is not known.

## What it does not show

TGrabs loads, processes and saves on threads of its own and the walk is one thread, so the figures compare
the programs as they are run and not their work a core. Its slow stretches, at about 750 fps with its
`proc` at 8 to 10 ms, were not explained. Where blobs' own time goes is in
`docs/findings/2026-11-12-blobs-contour-against-mask.md`.
