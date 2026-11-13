# On a thresholded crop, detect is a quarter of blobs and a third of the TRex port's labeling, and the bare walk is past the port's convert

2026-11-13, on v5-crop2 over 80462761 with `tools/detect.py` in the working tree, on an i9-14900KF, by
`docs/findings/experiments/2026-11-13-detect-on-a-thresholded-crop.py`, one OpenCV thread, every word
row-limited. The clip is `square-1.mp4` of
`video-tests/Thermal hysteresis 4 days/Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps-crops`,
a crop2 cut of 256 by 256 and 345595 rows at 60 fps, one dark ant on a light floor; the cut is 163, the
threshold of the folder's `speed output.json`, and the least area 20. The mask of that document is white
floor and a black ant, 99.7% of it set, so a labeling of its nonzero pixels finds the floor; every figure
below is of the dark pixels, by detect's `dark` or by the threshold inverted.

## A row, step by step, on held rows

ms a row over the clip's first 6000 rows, least of three, two runs of the script:

| step | ms |
|---|---|
| the Decoder's luma read | 0.125, 0.190 |
| threshold | 0.005, 0.009 |
| `detect.find` with `dark` | 0.045, 0.051 |
| `detect.find` on the inverted mask | 0.039, 0.041 |
| `blobs.find` on the inverted mask | 0.189, 0.204 |
| `connectedComponentsWithStats` over the plane | 0.132, 0.140 |
| the port's labeling: the plane labelled, then runs cut inside each kept box | 0.150, 0.154 |

One record on every row, two on 2 of the 6000; the area's median 187 pixels, 132 to 231 from the 5th
percentile to the 95th. The box round every dark pixel, which is what detect labels, had a median of 377
pixels of the plane's 65536 and was over a tenth of the plane on one row.

detect's records were blobs' on all 6000 rows at a least area of 1, in blobs' order, in each of the ten
columns detect has. Before its box was moved to an even corner they were blobs' in another order on 9 rows:
OpenCV numbers regions by blocks of two rows and columns.

## The walk, on one thread

`Graph.walk_row` over the first 20000 rows, nothing attached, a fresh graph each, the memo and the
decoder's cache at 16 MB each, two runs:

| | ms a row | rows a second |
|---|---|---|
| video as luma, threshold, detect with `dark` | 0.170, 0.211 | 5892, 4736 |
| video as luma, threshold inverted, blobs | 0.352, 0.367 | 2841, 2726 |

## TRex on the same rows

The first 30000 rows cut to a file of their own by a stream copy. Neither thresholds a frame as it
stands: both take a mean background of 100 samples and cut the absolute difference, here at 40, regions
of 19 pixels and up, and both write a pv, 5.88 MB.

| | rows a second |
|---|---|
| the port, `Code/Scratch/trex119-baseline/trex119.py convert`, one worker thread | 3410 |
| the port, eight | 4640 |
| TGrabs 1.1.9, `-nowindow`, one run | about 1650 over the run; its own line a second read 735 to 2880, median 881 |

## Through a thread pool

Threshold and a labeling over the 6000 held rows, rows a second at 1, 2, 4 and 8 pool threads, one run:

| | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| `detect.find` | 11391 | 8948 | 7636 | 7850 |
| `blobs.find` | 4643 | 5880 | 8618 | 7693 |
| the port's label and crop | 5043 | 9403 | 12448 | 11978 |

detect is slower on any second thread, as `runs.find` was in
`docs/findings/2026-11-13-sieve-against-the-trex-port.md` on v5-runs: its OpenCV calls are over a few
hundred pixels and the interpreter is held between them. On one thread it is where the port's labeling
is on four.

## What it does not show

The walk is bare: the worker's clip walk under a ledger was not run, and the v5-runs finding had it a
sixth under the bare walk on another document. The walk wrote nothing and the two TRex figures include a
pv written; the port's tracking was not run on its pv, nor `track` over detect's tables beyond three rows
in `tests/test_blobs.py`. One clip of twelve, its first rows, one animal on a clean floor: a plate with
speckle in opposite corners gives detect the whole plane, where its cost was not measured and is at least
the labeling's 0.13 ms. detect keeps no contour and no pixels, so `sample`, `inside`, `attach` and
`blobs-to-mask` read its record's box; what a contour or runs would add to it was not timed. The decode
is two thirds of the walk's row and was not looked at.
