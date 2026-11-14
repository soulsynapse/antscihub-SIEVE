# On the purb document a lane goes at most 76 ms between two rows with nothing wrong

2026-11-14, on v5-cleaning-up-monitor over 8ed3439f with the catalogue's `stalls` class in the working
tree, by `docs/findings/experiments/2026-11-14-how-long-a-lane-finishes-no-row-with-nothing-wrong.py`,
offscreen, one run. Whether the machine was otherwise in use was not noted. It is the sighting the Open on
the time a lane may finish no row asks for in `docs/spec/monitor.md`, and what `catalogue.STALLS` is set
past.

`video-tests/purb-settings.json`, its bake live, cold on a fresh Graph and Decoder under the Worker: the
window's 600 rows, then the clip for what was left of 40 seconds, 13329 of its 38100 rows. A lane's
stretch is from its last begin or progress, or the worker's last event in another lane or in none, to
its next begin or progress, by the clock at which each event was handed over: what `View.no_row_since`
holds, measured apart from it.

| lane | stretches | median, ms | 99th percentile | the longest | what they were under |
|---|---|---|---|---|---|
| window | 600 | 2.6 | 4.0 | 62.2, 4.2, 4.2 | the first row: the video's first read 48 ms, blobs 8, the two static nodes 4 |
| clip | 13330 | 2.9 | 4.4 | 76.1, 53.1, 24.1 | one step of track 73 ms at 11025 rows done and 50 at 6946; one run of crop 22 at 2867 |

The plan steps every chain node, track, count, size and travel, so nothing ran whole; region and
blobs-to-mask are static.

## What it does not show

Three rows long with nothing wrong are named in the spec, and the walk held one of them. A reader's
opening and a static node's one run were in the window's first row, at 62 ms together. A chain node run
whole was not: none is on this document since `size` steps, and one costs by the rows it is run over,
so on a clip of this length its last emits are the longest rows a healthy walk has and are of no size
this run bounds. The emit after a range's last row is no stretch of the class's, the walk being no
longer short of its range; the emits before it are. A seek on a file with long groups of pictures, a
video on a slow or a sleeping disk and a bake's reader opening a large file were not walked either.

`STALLS` is 5 seconds, some 65 times the longest seen. It is set by what is felt as a walk that has
stopped and by nothing measured between 76 ms and it; the first healthy document on which the class
fires says where the longest healthy row is, and is recorded beside this one.
