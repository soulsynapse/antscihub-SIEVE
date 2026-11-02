# TGrabs' ideas against the blobs path: runs, blob-local features, frame parallelism

2026-11-01, on v5-blob-detection over 5d66e58a, measured on the blobs tool as committed there; the
crop-first variant below became `find` in the same working tree afterwards, and the experiment,
`docs/findings/experiments/2026-11-01-trex-runs.py`, keeps the full-plane pass as the path it was
measured against. Rerun it for current figures. The file is
`video-tests/00000.MTS`, 1920×1080 at 59.94 fps, read as luma at scale 0.5 (960×540), rows 2000 to
2599, the finding of the same day's settings: threshold 79 inverted, blobs 230 to 17000 px, diff
255 − luma, core 205. Every stage is timed single-threaded on the 600 held frames, p50 over rows,
on a 32-core machine; the GUI, the memo and the worker are not in the path.

TRex v1.1.9's converter (TGrabs, read in its repo and its `commons` submodule) gets its speed from
three things: connected components computed on horizontal runs, with each blob's pixels gathered
from the run pointers rather than from a label image; every per-blob computation done inside the
blob's own lines, never over the plane; and eight frames in flight at once, threshold to serialized
record, with only the file append ordered. Its thresholding is plain OpenCV on `cv::Mat`. This asks
which of the three survives translation into numpy.

## Where a row's time goes today

| stage | ms, cv2 threads 32 | ms, cv2 threads 1 |
|---|---|---|
| decode, sequential, luma at 0.5 | 1.52 | |
| threshold | 0.11 | 0.15 |
| connectedComponentsWithStats | 0.96 | 1.77 |
| blobs.find, with diff | 7.72 | 7.62 |
| blobs.find, no diff | 5.38 | 5.87 |

136 components a row, p95 150, and one kept. The feature pass in `_records` is the cost, not the
labeling: on row 0, `np.nonzero` plus the gather is 1.1 ms, the five moment bincounts 0.3, mean and
core 1.2, peak through `np.maximum.at` 1.2, and two more full-plane scans (`labels > 0`, a second
`nonzero` for the diff) sit around them. All of it runs over the 25 661 masked pixels of 136
components before the area bounds drop 135 of them.

## The three ideas

| variant | ms, with diff | ms, no diff | records |
|---|---|---|---|
| current | 7.72 | 5.38 | |
| runs: moments from runs, mean and core from row cumsums | 13.72 | 5.63 | identical, every column |
| filter first: relabel to the kept components, then `_records` | 6.47 | | identical |
| crop first: `_records` inside each kept component's box | 1.36 | 1.34 | identical, contours included |

Runs do not pay. A vectorized run extraction over the plane is 2.5 ms on its own (2934 runs a row,
nearly all speckle), and the row cumsums that make mean and core O(runs) cost more in float64
over the full plane than the per-pixel bincounts they replace. TGrabs wins with runs because its
labeling emits them for free and its pixel gather is a `std::copy` from a pointer it already
holds; numpy has neither, and cv2's labeling at 1 ms is not the problem.

Filter first barely helps, which locates the cost: not the pixels under the mask but the plane.
Each operation that touches 960×540 int32 is 0.3 to 1 ms, and `_records` touches it four times
after relabeling, over mostly zeros.

Crop first is the one that lands, and it is TGrabs' second idea in numpy clothing: once the stats
say which components are kept, every feature is computed on `labels[y:y+h, x:x+w] == i`, a few
hundred pixels an ant, and the plane is read once by the labeling and never again. It gives the
same records to the bit, contours included, at 1.4 ms a row against 7.7, so the blobs node goes
from five decodes' worth to under one. Its cost scales with kept blobs times their box, so it
loses to the current pass only when kept blobs cover most of the plane, which the pile at 22 k px
over max_area does not reach. The with-diff and no-diff costs are now the same, so the diff input
stops being a 2.3 ms decision.

## Frame parallelism

threshold+blobs over the 600 held rows through a thread pool, the current `find`:

| workers | s, cv2 threads 32 | s, cv2 threads 1 | ms a row, threads 1 |
|---|---|---|---|
| 1 | 4.77 | 4.22 | 7.03 |
| 2 | 2.51 | 2.24 | 3.73 |
| 4 | 1.59 | 1.23 | 2.05 |
| 8 | 1.46 | 1.22 | 2.04 |
| 16 | 1.74 | 1.54 | 2.57 |

The GIL lets this scale to 3.6× and no further: cv2 and the large numpy calls release it, the
Python between them does not, and past 8 workers the contention costs more than the cores give.
OpenCV's own threads hurt once frames are parallel, a quarter at 8 workers, since 32 threads a
frame times 8 frames oversubscribe the box; a parallel walk should set them to 1. With crop-first
blobs in the same pool, 8 workers do the 600 rows in 0.31 s, 0.52 ms a row, under the decode.

Decode is 1.5 ms a row here, 660 rows a second, ffmpeg's threads already across the cores. Four
captures each on a chunk of the range reach 850 rows a second, 1.3× one capture, and eight are no
better: the box is already saturated by one capture's decode threads. So the ceiling for this file
is about 650 to 850 rows a second however the tools are arranged, and the pipeline today sits at
about 105 (1.5 decode + 7.7 blobs). Crop-first alone takes it to about 330 on one thread; the pool
takes the tools below the decode and leaves the decode as the whole cost.

The 1200 fps TGrabs was remembered at would need a lighter input than this: a `.pv` file read
back, a camera's raw frames, or smaller footage. At 1080p H.264 the decode alone forbids it on
this machine.

## Bytes a row for a mask

dense uint8 506 KB; packbits 63 KB; runs at 4 bytes each 11.5 KB; runs plus the pixels under them
36.5 KB (TGrabs' record); packbits then zlib level 1, 5.0 KB. The memo holds masks dense, 506 KB a
row at this scale, the same as the gray row they came from; a run or packed type would make the
mask's share of the memo 8 to 40 times smaller and leave the gray's as it is, so the memo's
capacity at most doubles. Every reader of a mask would then unpack it. Not argued for by these
numbers; recorded so the figure is here when the memo's accounting is next looked at.

## Who owns what

Crop-first is the blobs tool's alone: `find` and `_records` in `tools/blobs.py`, no player change,
no type change, same records. The `_split` path already works on a crop and would share the code.

Frame parallelism is the player's, and general: any frame tool whose heavy calls release the GIL
gains by it, blobs or not, and the clip walk is where it fits, a bounded range of rows walked off
the GUI with the memo written in row order, as TGrabs orders its appends. It is not a per-row
change: the worker's `walk_row`, the memo under its lock, and `frames()` reads that raise
`Cancelled` on a key change are all written for one computing thread, so the pool would be a
walk-level structure that hands each row's chain to a worker and merges in order, with cv2's
threads set to 1 for its duration. The sources spec's materialize step, one decode pass cutting
every rect of a plate off the GUI, is the same shape and the first customer.

The run representation is not adopted, on these figures, and the mask's bytes are a note, not a
proposal.
