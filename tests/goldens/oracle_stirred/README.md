# What is in this folder

Written by `sieve detect --csv`. Every row is one replicate's detection over
one node's per-frame signal, whose values are blocks. Frames are
absolute source frames.

## series.csv — what was measured, one row per frame

| column | meaning |
|---|---|
| `replicate` | which arena; `baseline` when the project defines none |
| `node_id` | the graph node the signal was taken from (a generated id) |
| `filter` | that node's filter, for reading and for plot legends |
| `frame` | absolute source frame |
| `time_seconds` | when `frame` is, to the millisecond; `NA` if the source states no rate |
| `blocks_total` | blocks this frame was divided into |
| `blocks_in_band` | how many of them fell inside the value band |
| `blocks_in_band_fraction` | the same, over `blocks_total` |
| `windowed_mean_blocks` | `blocks_in_band` averaged over the detection window |
| `windowed_mean_fraction` | the same, over `blocks_total` — **the count threshold is compared against this** |
| `detected` | whether the threshold was met; `NA` where the detector is disarmed |

## intervals.csv — what was claimed from it

| column | meaning |
|---|---|
| `replicate` | which arena; `baseline` when the project defines none |
| `node_id` | the graph node the signal was taken from (a generated id) |
| `filter` | that node's filter, for reading and for plot legends |
| `start_frame` | first detected frame, inclusive |
| `end_frame_exclusive` | one past the last detected frame |
| `start_seconds` | `start_frame` in time |
| `end_seconds` | `end_frame_exclusive` in time |
| `duration_frames` | `end_frame_exclusive - start_frame` |
| `duration_seconds` | the same, in time |

A present-but-empty `intervals.csv` means a detector ran and claimed nothing.
An absent one means no replicate was armed — the two are not the same, and
that is why the file is missing rather than empty.

## The settings these numbers were taken under

### arena-1

- signal node: `blocks` (`block_signal`), 20 fps
- frequency band: 7 and above Hz
- value band: 1e+06 and above
- detection window: 9 frames, centered
- count threshold: 0.25 and above of `blocks_total`

### arena-2

- signal node: `blocks` (`block_signal`), 20 fps
- frequency band: 7 and above Hz
- value band: 1e+06 and above
- detection window: 5 frames, centered
- count threshold: 0.25 and above of `blocks_total`
