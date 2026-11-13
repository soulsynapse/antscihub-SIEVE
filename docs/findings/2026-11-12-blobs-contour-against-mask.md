# A record's contour is a tenth to a sixth of what blobs costs, and a mask in its place is not smaller

2026-11-12, on v5 at 2ded1da6 with an i9-14900KF, by
`docs/findings/experiments/2026-11-12-blobs-contour-against-mask.py`, offscreen. The question was whether
`tools/blobs.py` would be much faster keeping each region's binary mask where it keeps a traced contour,
every reader of the contour but the painter filling it back to a mask through `_table.footprint`.

## What was timed

The masks a document's blobs node is fed were computed once through its graph and held, so each variant
ran on the same input with no decode in it, three times interleaved, with `cv2.setNumThreads(1)`. `trace`
is `blobs.find` as it is; `none` the same with no contour; `mask` with the region's bool crop, which
`_records` has already made, in the contour column; `label` is `connectedComponentsWithStats` and the cast
before it alone. No document here turns `split` on and the scratch tool has none.

| ms a row, least and most of three | bg-subtract-compare, 234 by 304, 3000 rows | purb-168-178, 960 by 540, 590 rows |
|---|---|---|
| trace | 0.502 to 0.545 | 1.985 to 2.104 |
| none | 0.415 to 0.431 | 1.790 to 1.851 |
| mask | 0.439 to 0.447 | 1.775 to 1.821 |
| label | 0.185 to 0.213 | 1.420 to 1.534 |
| records a row, of components labelled | 3.12 of 16.4 | 18.84 of 146.0 |

The contour is 0.09 ms of 0.50 on the first and 0.19 of 1.98 on the second. Keeping the mask is 13% and
11% under blobs as it is. The labeling is 37% of the first and 72% of the second; what is left is the
record loop, and a profile of the first document puts it in `_table.moments`, whose `np.nonzero` over each
region's crop was 35 us a call against `findContours`' 25.

A bare walk of the same rows with the scratch tool in the graph in place of blobs did not resolve the
difference: 1.36, 0.87, 0.94 and 1.50 ms a row on the first document, as it is and keeping the mask by
turns, and 3.80, 3.91, 4.08 and 4.32 on the second.

## What a row holds

| bytes a row as `graph.nbytes` counts them | bg-subtract-compare | purb-168-178 |
|---|---|---|
| trace | 7033 | 8785 |
| none | 187 | 1130 |
| mask, a bool a pixel of the box | 58633 | 11145 |

A bool crop is eight times the contour where the regions are large and a quarter over it where they are
ants. A bit a pixel would be an eighth of the crop. Runs were not built.

## What a reader pays, and what it reads

`_table.footprint` on a record took 89 us from a contour and 60 from a mask on the first document, 24 and
17 on the second.

The filled contour was not the region's mask for 8530 of 9351 records on the first document and 10362 of
11115 on the second. `RETR_EXTERNAL` drops holes and `fillPoly` fills what the outline encloses, so
`sample`, `inside`, `attach` and `blobs-to-mask` read pixels the labeling did not give the region. By how
many pixels was not counted, nor whether a hole or a one-pixel concavity is the commoner cause.

## OpenCV's threads

With `cv2.setNumThreads` at the machine's 32, every variant on the first document was slower than at 1,
`trace` 0.726 to 0.877 against 0.502 to 0.545; on the second the labeling was faster at 32, 1.18 against
1.42, and `trace` the same within the spread.

## A labeling by runs, built the next day

`tools/runs.py` was written on 2026-11-13 over the same tree: each row cut into runs, a run joined to those
it touches in the row above, and area, box and moments summed over runs, with the region's runs in a `runs`
column where blobs has `contour`. Timed by the same experiment on the same masks, beside blobs as it is:

| | bg-subtract-compare | purb-168-178 |
|---|---|---|
| blobs, ms a row, one OpenCV thread | 0.501 to 0.553 | 2.012 to 2.107 |
| runs, ms a row | 0.230 to 0.261 | 0.530 to 0.632 |
| runs with OpenCV at 32 threads, which it does not call | 0.246 to 0.273 | 0.546 to 0.608 |
| blobs, bytes a row | 7033 | 8785 |
| runs, bytes a row | 3837 | 4936 |
| `footprint` of a record, contour and runs, us | 97 and 101 | 26 and 27 |

Its records are blobs' in every column but the last, in another order, a region placed by its first run
where OpenCV numbers by blocks of two rows; its footprint is the region's own mask for every record of both
documents, 9351 and 11115. A bare walk with runs in the graph in place of blobs read 1.00 and 0.65 ms a row
against 1.27 and 1.44 on the first document, and 2.57 and 2.38 against 3.71 and 4.08 on the second.

## What it does not show

The masks are of two documents and the first rows of each, neither with a diff wired, so the diff's columns
and `split` were timed on neither; `tests/test_blobs.py` holds runs to blobs' records with both on. Whether
a table of runs frees the walk from the slowing a process showed over a clip,
`docs/findings/2026-11-12-bg-subtract-against-tgrabs.md`, was not looked at: a record still holds an object.
