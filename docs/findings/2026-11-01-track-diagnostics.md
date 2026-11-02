# Track diagnostics on the purb document: where the linker's ids break, read from the linker itself

2026-11-01, on v5-blob-detection over 896113f7, by docs/findings/experiments/2026-11-01-track-diagnostics.py
on video-tests/purb-settings.json, rows 2000 to 2599 of video-tests/00000.MTS, ten seconds at 59.94
fps, luma at 0.5 (960×540). The document's settings: threshold 72 inverted, blobs 90 to 6731 px with
split on and core 65, track at its defaults (max_step 4, lost_rows 30, min_rows 3, min_p 0.1). No
ground truth; everything below is what the greedy pass can see about its own choices, which cannot
count a swap between two tracks that were never lost.

The scene is a dish with a cluster of about a hundred ants and eight or nine loose ones (row 2300 is
the frame looked at). The cluster is one region of 22.9 k px at this threshold, over max_area, and
split cuts it at rising diff levels into whatever pieces fall inside the bounds first, 7.2 a row,
against 8.8 blobs a row outside it with area p50 185 px.

## The tool's pass

| | |
|---|---|
| ids minted / confirmed at 3 rows | 146 / 38 |
| rows seen per confirmed id | p50 190, p95 589 |
| consecutive-row step | p50 0.3 px, p95 1.3, max 3.8; none over max_step |
| assignments contested (a rival pair sharing the track or blob with p ≥ half the winner's) | 338 of 9298, 3.6% |
| reacquisitions (a take over a gap) | 488, gap p50 3 rows, jump p50 0.5 px, p95 10, max 92 |
| jumps over 2×max_step / 10×max_step | 32 / 5 |
| absorbed (a live track unassigned, its prediction inside a blob another id took) | 202 |
| births beside a blob of the row before / elsewhere | 5 / 141 |

Where the events sit, with the cluster taken as the box (330, 160) to (520, 300): 333 of the 338
contested assignments, 172 of 202 absorptions, 315 of 488 reacquisitions, 22 of the 32 jumps over
8 px, and 48 of 141 births. The ids absorbed most (21, 6, 8, 20, 3, 18 at 17 to 40 times each) are
cluster fragments. The teleports and the identity churn the GUI shows are, by this measure, almost
all the linker tracking pieces of the cluster that the split tool emits and withdraws as the ants in
it move; a fragment vanishes, its id waits up to 30 rows with a reach of 4 px a row, and takes the
next fragment to appear within 120 px.

Outside the cluster the loose ants link cleanly: steps are two orders under max_step, five
contested assignments in 600 rows, and the 173 reacquisitions there have a median gap of 3 rows, an
ant dipping under the threshold for a few rows rather than being lost. The 93 births outside are
mostly specks confirmed in under 3 rows (108 of 146 ids never reach 3 rows) and the ants climbing
the ramp at the top right of the dish, where the wall's shade meets the threshold.

## Variants, same rows, same detections

| linker | ids / confirmed | contested | reacquisitions | jump p95 / max px | over 2×max_step | absorbed |
|---|---|---|---|---|---|---|
| tool: reach gap×max_step, lost 30 | 146 / 38 | 3.6% | 488 | 10.0 / 91.8 | 32 | 202 |
| reach √gap×max_step | 172 / 43 | 0.2% | 377 | 2.7 / 11.6 | 5 | 112 |
| reach max_step, flat | 182 / 46 | 0.0% | 367 | 2.1 / 3.8 | 0 | 109 |
| tool's reach, lost 5 | 236 / 87 | 0.1% | 313 | 5.9 / 12.6 | 11 | 94 |

The linear reach is what makes the jumps: capping it at √gap removes 27 of the 32 long jumps and
94% of the contested assignments while keeping 377 of the 488 reacquisitions, and the confirmed ids
rise by five, not the hundreds a shorter lost window costs (lost_rows 5 doubles the confirmed ids and
cuts the median id to 21 rows). The flat reach loses nothing an ant actually does on this clip, since
no consecutive step exceeds 3.8 px, but the clip has no ant walking lost for 30 rows either, so that
is the clip's property and not the rule's.

## What this says

The cluster should not be blobs. At this scene's density nothing below visual identification or
tags resolves ids inside it, and split hands the linker a shifting set of fragments that produce
nearly every contested assignment, absorption and teleport in the record. The clean measurement is
the loose ants with the cluster as a region, either excluded by max_area with split off, or a mask
the pile's own blob paints (see docs/spec/blob-tools.md). The cluster's own quantity is a size and a
count of ants at its edge, not tracks.

The reach rule is the linker's one defect this clip exposes, and √gap is the least change that fixes
what is measured here. It was tried the same day and not adopted: the linear reach is the rule a
walking ant obeys, √gap fits this clip's lack of long walks under the threshold, and what it costs an
ant lost longer is the clip the diagnostics cannot supply. A swap between two loose ants in the open
is invisible to every row above, and only a labelled segment counts those. The events csv the experiment writes, one line per row and
kind with the id and position, is how to scrub to the rows worth labelling.

## The crossings clip, 168 to 178 s

Kendrick picked the segment as the one with everything: flicker at the cluster's edge, loose ants
overlapping, swaps and teleports in the open. It is cut to video-tests/00000_168-178.mp4 (ffmpeg,
-ss 168 -t 10, libx264 crf 12, 590 rows) with video-tests/purb-168-178.json the purb document
pointed at it, both outside git with the footage. Same settings, rows 0 to 589. The cluster is the
one region over max_area every row, so here "inside" is that region's own box that row, padded 8 px,
rather than a fixed rectangle.

| | tool's pass | inside the cluster | √gap reach | flat reach |
|---|---|---|---|---|
| blobs a row | p50 20 | | | |
| ids / confirmed | 64 / 58 | | 72 / 62 | 78 / 64 |
| contested | 435, 3.8% | 245 | 4 | 0 |
| reacquisitions | 339 | 249 | 330 | 324 |
| jump p95 / max px | 8.3 / 83.7 | | 1.6 / 11.6 | 1.0 / 3.9 |
| jumps over 2×max_step / 10×max_step | 18 / 6 | 11 / 6 | 7 / 0 | 0 / 0 |
| absorbed | 238 | 153 | 227 | 223 |

Unlike rows 2000 to 2599, this segment has the loose-ant events Kendrick wants measured: 190 contested
assignments, 85 absorptions, 90 reacquisitions and 7 of the 18 long jumps are outside the cluster,
54 of the contested ones in the first 50 rows, where the group of ants at the ramp top right crosses
and overlaps. The six jumps over 40 px are all cluster-edge (ids 12, 40, 33 at rows 443, 400, 415,
207) or the ramp (ids 61, 18, 4 at rows 585, 17, 15), gaps of 9 to 29 rows. √gap again takes the long
jumps out and the contested share to near zero at a cost of eight ids. Absorptions barely move with
the reach, as they should: a merge is the detector's event, not the linker's, and the split-off half
of it is counted in the births beside a blob, 6 here. Those 238 absorptions, 85 of them in the open,
are the row-level list of where a swap can have happened on this clip, which is what to label.
