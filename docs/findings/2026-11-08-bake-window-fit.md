# The window with rescale live, then baked: what the bake buys, and on which clip

2026-11-08, on v5 at 5b96276e, the merge of the bake branch, read off `sieve_player/dev/monitor.py`
driving the player's own Graph and Worker offscreen through
`docs/findings/experiments/2026-11-08-bake-window-fit.py`. Two documents. The crossings document,
`video-tests/purb-168-178.json` on `00000_168-178.mp4`, 1920×1080 at 59.94 fps, 590 rows, whose
format-1 scale loads as a rescale node: video → rescale 0.5 → threshold → blobs, with track, size,
count and travel as the series chain; the window is the whole clip, which is also the player's 10 s
default. And a 5.3K GoPro clip, `GX010047c2_02_17_26.MP4`, 5312×2988 at 23.976 fps, under video →
rescale 0.5 → threshold with no series chain, over the player's 240-row window. In both a bake node
is spliced after rescale and baked lossless over the window. Limits are the player's defaults, memo
and decoder cache 4 GB each, except where a run says otherwise. Numbers are one run each; the
plate's decode step varied between 8.4 and 13 ms a row across runs on the 5.3K file, so a timing
difference under about a third is noise, while the read counts are exact.

## What a row costs in each store, and whether the window fits

| per row | 1080p luma | 5.3K luma |
|---|---|---|
| plate frame, decoder cache | 1.98 MB | 15.1 MB |
| the 10-s window in the cache | 1.14 GB, 3.5 windows at 4 GB | 3.55 GB, 1.1 windows at 4 GB |
| served frame at 0.5, the reader's cache | 0.49 MB, 14 windows | 3.8 MB, 4.5 windows |
| memo, rescale + bake + threshold (+ blobs) | 1.49 MB, 4.6 windows | 11.4 MB, 1.5 windows |

At the default limits the 1080p plate fits the window three times over, so on the crossings clip
the fit was never the question. The 5.3K plate fits once, with nothing to spare: a 20-s window, or
a second video-reading branch, puts it under one, and the first finding's LRU result then holds
exactly, measured below. Baked at half scale the same window costs the reader a quarter, and the
reader takes the plate decoder's limit, so the served window fits whatever the plate's did.

## Where the decoder cache is touched, and when the bake spares it

A rewalk over a window the memo holds never reaches the decoder, live or baked, so a cache short
of the window costs nothing until a change lands upstream of what the memo holds. The change here
is rescale's knob; threshold's would rerun threshold and blobs only in both modes.

| walk | cache | decodes | cached reads | wall |
|---|---|---|---|---|
| 1080p live, cold | 4 GB | 590 | 0 | 7.1–7.7 s |
| 1080p live, rewalk | 4 GB | 0 | 0 | 4.2–5.0 s |
| 1080p live, rewalk after a change on rescale | 1 GB, 0.9 windows | 590 | 0 | 9.3 s |
| 1080p baked, cold | 1 GB | 0 on the plate; 590 on the file | 590 on the file | 7.7–8.7 s |
| 1080p baked, rewalk after a change on rescale | 1 GB | 0 | 0 | 5.2 s |
| 5.3K live, cold | 4 GB | 240 | 0 | 3.2–5.4 s |
| 5.3K live, rewalk after a change on rescale | 4 GB, 1.1 windows | 0 | 240 | 3.5 s |
| 5.3K live, rewalk after a change on rescale | 2 GB, 0.6 windows | 240 | 0 | 4.1 s |
| 5.3K baked, cold | 4 GB | 0 on the plate; 240 on the file | 240 on the file | 2.3–3.9 s |
| 5.3K baked, rewalk after a change on rescale | 4 GB | 0 | 0 | 0.02 s |

The cache at 0.9 and at 0.6 windows answered zero reads on the change, the cyclic-scan LRU result
of 2026-10-31 again; at 1.1 windows it answered every one. Baked, the plate decoder's counters did
not move through any walk, cold or after the change: the change marks the node stale and the file
keeps serving, so the rewalk is the memo's alone, 0.02 s on the GoPro document and the series
chain's time on the crossings one.

## What a cold row costs, live and baked

| per row | 1080p live | 1080p baked | 5.3K live | 5.3K baked |
|---|---|---|---|---|
| plate decode (video) | 1.2 ms | 0 | 8.4–13 ms | 0 |
| rescale | 0.13 ms | 0 | 1.0 ms | 0 |
| served read, the file's decode | – | 0.39 ms | – | 2.8–5.4 ms |
| threshold | 0.05 ms | 0.10 ms | 0.75 ms | 1.3 ms |
| blobs | 2.5 ms | 2.8 ms | – | – |
| series chain, per row of the walk | 6.7–7.5 ms | 8–9 ms | – | – |
| the walk, whole | 12–13 ms | 14–17 ms | 13–22 ms | 14–18 ms |

The bake replaces the plate's decode and rescale, 1.3 ms at 1080p and 9–14 ms at 5.3K, with the
half-scale file's decode, 0.4 and 3–5 ms. That is the whole of what it buys a cold walk, and on the
GoPro document it is most of the row. On the crossings document it is a tenth: the row is the
series chain. track runs over the stack so far at every emit, twenty times across the 590-row
window at 200–250 ms each, 4–5 s of the 7 s cold walk and the whole of the 4–5 s rewalk, and the
bake has nothing to say to it. The baked cold walk on this clip was not faster than the live one,
which is noise around that fact. The next cost on the ants pipeline is the chain rerun per emit,
quadratic in the window, not the decode.

## The bake itself, and the file

| | 1080p, 960×540 gray | 5.3K, 2656×1494 gray |
|---|---|---|
| rows baked | 590 | 240 |
| wall | 1.9–2.0 s, 300 rows/s | 4.3–4.5 s, 55 rows/s, 2.3× realtime |
| on disk, lossless | 51 MB, 0.087 MB/row | 274 MB, 1.14 MB/row |

Lossless on the ants footage, a static background under a few moving animals, is thirteen times
smaller a row than on the GoPro's, so an hour of the GoPro at half scale is of the order of 100 GB
in the store, and the standard quality is the one to measure next on that footage, against the
mask it feeds.

## Three things seen on the way

A live bake node is the identity, returning its input's array, and the memo holds that array a
second time under the bake's key, counting its bytes again: 3.8 of the 11.4 MB a 5.3K row costs the
memo, a third, is a live bake node, and on the GoPro document the memo reached its 4 GB and evicted
during the run where without the node it would not have. The RAM is not spent, since it is one
buffer; the capacity is, because `Memo` sizes by `nbytes` and not by buffer. Whether a "same" tool's
result is memoized at all, or the memo counts a buffer once, is a decision, not made here.

A served frame node is not memoized: each consumer of the node at a row reads the file's reader,
two reads a row here, the walk's and threshold's, the second from the reader's cache at 0.01 ms.
Nothing to act on; the first read is the file's decode and the second is free.

The monitor's cache lane is the plate decoder's. Baked, that lane sits at whatever the live walks
left in it, frames nothing reads, while the store that serves the window is the reader's cache,
which the monitor does not show. When the lanes are drawn per store, as the first finding asked,
the served readers are stores.
