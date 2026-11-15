# A video loaded over another left the first's cache and memo resident, and a capture on a large plate holds about a gigabyte no store counts

2026-11-15, on v5-crop2-serves-its-clips over bfb0d3a0, by
`docs/findings/experiments/2026-11-15-what-an-unloaded-video-still-holds.py` and the history a monitor
report saved, `sieve-history-20261115-115320.json`, of `video-tests/GX010047c2_02_17_26.MP4`, 5312x2988
read as luma. The report said SIEVE held 17.1 GB resident while the stores it listed held 6.1 GB.

## What the history shows

Resident bytes less every store's, bucket by bucket: 10.9 GB at the history's first bucket, when the
stores held 0.26 GB, and between 10.2 and 11.0 GB at every bucket after, through two clip walks and the
video cache filling to its limit. The ledger is made when a video is opened, so the history's first
bucket is an open: the process held the 10.9 GB before this video had read a row.

## What held it

Over bfb0d3a0, `rep3_intermittent_crop.MP4` opened in a PlayerWindow offscreen, walked four seconds, and
`00000_168-178.mp4` loaded over it: the first's Graph, Decoder, Worker, Ledger and Emitter were all still
referred to after a collection, its cache counting 361 MB and its memo 120 MB. The Worker was held by the
slots connected to its own signals, one of them a lambda holding the Worker as a default, and the Graph by
the Worker's lanes. `Decoder.close` released the captures and kept the frames; `Graph.close` closed the
readers and kept the memo. A video open with both stores at their limits and a served clip's reader beside
them is of the size the history shows.

With the tree's `_unload`, `Graph.close` and `Decoder.close`: all five gone after the collection. With the
stores emptied at close and the connections left as they were, the five were held and counted 0 MB.

## What a capture holds

One Decoder on the plate, resident MB beside what its cache counts:

| | resident | cache |
|---|---|---|
| opened | 86 | 0 |
| 30 rows stepped on the walk's cursor | 1517 | 454 |
| the scrub's cursor sought to 3000 | 2535 | 484 |
| the scrub's cursor sought to 6000 | 2566 | 515 |
| the walk's cursor sought to 5000 | 2598 | 545 |
| the walk's cursor sought to 9000 | 2628 | 575 |
| the cache emptied, both captures open | 2053 | 0 |
| closed | 71 | 0 |

About 1 GB a capture once it has decoded, 2 GB for the plate's two cursors, in no store the monitor lists
and under no limit. It did not grow with a second seek on either cursor. One run; what in the capture
holds it was not looked into.
