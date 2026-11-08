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

## Second half: the same window once the chain's prefix steps

2026-11-08, on v5-solver at 2712d0d3, the stepping walk of docs/spec/solver.md landed, through
`docs/findings/experiments/2026-11-08-stepped-chain.py` over the crossings document with no bake
node, and `2026-11-08-bake-window-fit.py` again with one. The plan steps track and travel and runs
size and count whole; a stepping node's runs below are its steps. One run each, as above.

| walk | before, above | stepped |
|---|---|---|
| live, cold | 7.1–7.7 s | 3.3–4.0 s |
| live, rewalk | 4.2–5.0 s | 0.60–0.74 s |
| baked, cold | 7.7–8.7 s | 3.8 s |
| baked, rewalk after a change on rescale | 5.2 s | 0.8 s |

| per window of 590 rows, every 30 | runs | per run | summed |
|---|---|---|---|
| track, stepped | 590 | 0.57–0.89 ms | 0.34–0.50 s |
| travel, stepped | 590 | 0.05–0.07 ms | 0.03–0.04 s |
| size, whole | 20 | 4.5–6.2 ms | 0.09–0.10 s |
| count, whole | 20 | 0.01–0.02 ms | 0.00 s |

The series chain is 13–14% of the cold walk, where it was most of it, and the rewalk is the
prefix's steps plus size: track's 4–5 s a window became 0.3–0.5 s, linear in the rows. What is left
quadratic is the suffix, and on this document the suffix is size, a median over the stack per emit
at 5 ms. The rewalk at four cadences:

| every | emits | rewalk | size summed |
|---|---|---|---|
| 30 | 20 | 0.74 s | 0.10 s |
| 10 | 59 | 1.06 s | 0.37 s |
| 3 | 197 | 1.88 s | 1.14 s |
| 1 | 590 | 3.49 s | 2.64 s |

At every row the rewalk is back near the cold walk's time and three quarters of it is size. size
and count read one row, and the spec's Why says so, but they run whole, so each emit pays them over
the stack; a cadence shorter than thirty on the ants documents costs size, not track. With
tracks-filter and resolve spliced under track, lo 3 on rows and `area` as resolve's column so the
pass does its whole work on tables with no tag, the plan reads track step, tracks-filter whole,
resolve whole, travel whole by resolve:

| per window, every 30 | runs | per run | summed |
|---|---|---|---|
| tracks-filter | 20 | 11.2–11.5 ms | 0.22–0.23 s |
| resolve | 20 | 52–54 ms | 1.05–1.08 s |
| travel, whole by resolve | 20 | 9–11 ms | 0.18–0.22 s |

The rewalk with them is 1.9 s, 1.5 s of it the suffix; at every row it would be of the order of 45 s.
So "cheap" held at thirty and does not hold at one: the cadence is bounded by the suffix's cost per
emit wherever a whole-window tool is in the chain, and the Worth a look's question of a shorter
cadence has the answer that it is the suffix's to pay. travel under resolve runs whole at 9–11 ms
where it stepped at 0.05, which is the rule working as written.

Seen on the way. The monitor reads 589 steps of 590 on a rewalk: the first row's step lands before
the new walk's first progress event and is counted to the walk before, then reset. On the chain
with resolve the summary says 104% in series nodes and −4% unprobed: the closing emit lands after
the last progress event, outside the wall the monitor measures and inside the node totals, 75 ms of
1.9 s. And a tool that raises at every run ends the worker thread: `_serve`'s handler closes the
range, the close emits the chain, the chain raises again inside the handler, and the thread dies
with a traceback where fe462c3b meant `failed` to name the row and the node. tracks-filter with a
node that lacked its `column` default did it here; a column the tables lack would do it in the GUI.
