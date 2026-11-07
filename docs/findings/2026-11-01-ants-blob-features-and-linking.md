# Blob features and linking on the ants clip: what the records look like at the working settings

2026-11-01, on v5-blob-detection over f0b66582 with the working tree that added the blob record's
moments, intensity and contour columns, the filter, track and travel tools. The file is
`video-tests/00000.MTS`, 1920×1080 at 59.94 fps, 38100 rows, read as luma at scale 0.5 (960×540).
Kendrick's settings: threshold 79 inverted, blobs 230 to 17000 px. The diff plane handed to blobs
is 255 − luma, with core_threshold 205, so core is the pixels at luma 50 or darker. Features are
over 40 rows spaced across the clip; linking is over rows 2000 to 2599, one run each, through the
tools off the GUI.

## The records

Percentiles over every region of the mask, split by the area bounds. 1.0 px regions dominate the
speckle so its shape columns are degenerate.

| | n | per row | area p5 / p50 / p95 | major p50 | minor p50 | aspect p50 | mean p50 | core_ratio p50 |
|---|---|---|---|---|---|---|---|---|
| under 230, dropped | 4724 | 118 | 1 / 2 / 167 | 2.0 | 0.0 | | 183 | 0.0 |
| 230 to 17000, the loose ants | 83 | 2.1 | 230 / 257 / 552 | 41.1 | 11.4 | 3.6 | 205 | 0.6 |
| over 17000, the pile | 40 | 1.0 | 21246 / 22048 / 22985 | 224 | 170 | 1.3 | 209 | 0.7 |

Two things in the ants' row. The area cut sits inside their distribution: p5 is 230.1 and p25 is
235, against a cut of 230, so an ant's region crosses the cut from row to row and the detection
flickers. And core_ratio is the same 0.6 for the ants and 0.7 for the pile, so at this threshold the
second cut separates nothing: a mask at luma 79 holds no shadow fringe, since the shadows are far
brighter than that, and core measures how much of each ant is darker than 50, which is its body
against its legs. The column earns its place only on a mask cut loose enough to take shadow in.

Aspect does separate: 3.0 to 4.3 across the ants' quartiles, 1.3 for the pile, and a speck near 1
or undefined.

## Cost

blobs.run with the diff input, moments, intensity and contours: median 5.5 ms a row, max 9.1 ms, at
960×540. Splitting on, the pile's 22 k px region is searched and nothing within the bounds comes out
of it, as expected of a pile, costing 17 ms for that row and leaving the output unchanged.

## Linking

600 rows from 2000, track at its defaults (max_step 12 px, lost_rows 30, min_rows 3, min_p 0.1):
detection 9.1 s, linking 42 ms. Steps between linked rows are p50 0.3 px, p95 1.5 px, so a step is
two orders under the spacing between loose ants and the greedy match is never ambiguous off the
pile. The tracks are short all the same: 9 ids over the window, lengths p50 7 rows, p90 146, max
211, median 1 confirmed track a row. That is the area cut above, not the linker: an ant that drops
under 230 px for over 30 rows ends its track and starts another on return. Lowering min_area into
the gap under the ants' distribution, or raising lost_rows, is where to look first; a hand-labelled
segment is what would say which, and neither has been tried.
