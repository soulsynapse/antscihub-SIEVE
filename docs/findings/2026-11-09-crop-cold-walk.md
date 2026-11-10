# The crossings window after a crop to the dish: what the crop buys each tool, and what the walk charges for the region beside it

2026-11-09, on v5-region at 50d07ce7, read off `sieve_player/dev/monitor.py` driving the player's own
Graph and Worker offscreen through `docs/findings/experiments/2026-11-09-crop-cold-walk.py`, beside
the uncropped figures of docs/findings/2026-11-08-bake-window-fit.md, whose uncropped walks are rerun
here on the same tree so the comparison is one commit's. The crossings document,
`video-tests/purb-168-178.json` on `00000_168-178.mp4`, 1920×1080 at 59.94 fps, 590 rows, the window
the whole clip: video → rescale 0.5 → threshold → blobs, with track, size, count and travel as the
series chain, the chain's prefix stepping. The cropped runs splice video → region → blobs-to-mask →
crop.roi and video → crop → rescale, the region reading `00000_168-178.nest.geometry.json`, a file
written by hand on 2026-11-09 and not by a drawing utility, narrowed to one of its circles: `dish`,
the whole dish, 797×797 of the plate, 31% of its pixels, or `pile`, the cluster alone, 461×461, 10%.
The dish circle sits on the dish's rim by eye, overlay in the session's scratchpad; whether a drawn
outline lands where it was drawn is still the Worth-a-look under Region. A bake node sits after
rescale in every run, live until the bake phase. Limits are the player's defaults, memo and decoder
cache 4 GB each. Uncropped and dish are two runs each, pile one; the uncropped figures agree with the
2026-11-08 finding's stepped column.

## The walks

| walk | uncropped | dish | pile |
|---|---|---|---|
| live, cold | 3.3–3.4 s | 6.0–6.1 s | 4.5 s |
| live, rewalk | 0.42 s | 0.40–0.43 s | 0.32 s |
| live, rewalk after a change on rescale | 3.4–3.6 s | 1.9–2.0 s | 1.2 s |
| bake after rescale, lossless | 1.8–2.0 s, 51 MB, 960×540 | 0.8–0.9 s, 20 MB, 398×398 | 0.5 s, 7.9 MB, 230×230 |
| baked, cold | 3.0–3.1 s | 1.8–1.9 s | 1.1 s |

count read 18.9 blobs a row, 10775 records over the window, uncropped and cropped to the dish alike,
so the dish cut lost no ant the threshold found; cropped to the pile it read 7.3 a row, the ants
outside the cluster gone, which is the cut doing what it says.

## What a cold row costs per node

| per row | uncropped | dish | pile |
|---|---|---|---|
| video, the plate's decode | 1.10 ms | 1.19 ms | 1.16 ms |
| region | – | once, 11 ms | once, 10 ms |
| crop | – | 0.70 ms | 0.68 ms |
| rescale | 0.11 ms | 0.08 ms | 0.03 ms |
| blobs-to-mask | – | 1.94–1.99 ms, 1.98 MB | 0.82 ms, 1.98 MB |
| threshold | 0.04 ms | 0.03 ms | 0.02 ms |
| blobs | 2.34–2.48 ms | 1.66 ms | 0.97 ms |
| memo per row | 1.49 MB, 4.6 windows | 3.07 MB, 2.3 windows | 2.35 MB, 3.0 windows |

Every plane-touching tool after the cut got cheaper, as the spec's Why claims: on the dish blobs
2.4 → 1.7 ms, the bake's file and wall under half, the served read 0.26 → 0.16 ms, rescale and
threshold proportionally, and the walk that pays only those, the rewalk after a change on rescale,
went from 3.5 to 1.9 s, the baked cold walk from 3.0 to 1.8. On the pile each is smaller again and
the two walks are 1.2 and 1.1 s. That is the number the branch was for, and it holds.

The cold walk got slower, 3.4 to 6.0 s on the dish, and the two rows of the table say where. The
window walk folds a density for every frame node at every row (`_Walk.turn` in
sieve_player/worker.py, where `planes` is every fed frame node), so blobs-to-mask, which crop reads
at row 0 alone, is computed at all 590 rows and memoized at all 590, a full-plate mask of 1.98 MB a
row at 1.9 ms: 1.1 s of the walk and 1.2 GB of the memo, the memo's windows halved. STATIC is
declared per tool and not propagated, the Facts under Crop already say, so a blobs-to-mask fed by a
static region is static in fact and per-row in the plan, and the fold charges the difference. The
same would be charged for any node that reads a static table into a plane. The other 0.4 s is
crop's own: `rect` scans the whole plate mask for its nonzero extent at every row, 0.47 ms of the
0.70, against 0.14 for the cut's copy, because the rect is recomputed per run and memoized nowhere.
Both are the walk's accounting of a static thing as a per-row one; neither is the cut.

Uncropped, the row is 1.1 ms of decode, 2.5 of blobs and the chain; cropped to the dish and with
both charges gone, it would be 1.2 of decode, 0.14 of cut, 1.7 of blobs and the chain, of the order
of 2.5 s a window against 3.4, which the rewalk-after-rescale column measures as 1.9 against 3.5
without the decode. So the crop makes the cold walk faster by about a quarter on this document once
the static chain upstream of its roi is run once, and slower by three quarters until then; the
spec's Why said the crop is not what makes a cold walk faster, and the decode's share was that
claim's reason. On this clip at this scale the decode is a third of the uncropped row, and blobs
most of the rest, so the crop's gain is bounded by blobs' and the chain's share.

## Second half: the same window once static is inherited and the rect is OpenCV's

2026-11-09, same tree with two changes, both landed on v5-region after this measurement: the plan
marks a frame node static when every node feeding it is, so blobs-to-mask after region runs once,
holds once and folds once, the way Houdini propagates time dependence down a SOP chain and cooks a
time-independent node once; and crop's rect reads `cv2.boundingRect` over the mask instead of two
numpy reductions, the same four numbers at a quarter of the scan. The monitor reads static off the
plan's entry now, not the tool's declaration, and leaves a static node's bytes out of the memo's
per-row projection, which it had counted for region too. Two runs each, uncropped one, the same
script.

| walk | uncropped | dish, before | dish, after |
|---|---|---|---|
| live, cold | 3.3–3.5 s | 6.0–6.1 s | 2.5 s |
| live, rewalk after a change on rescale | 3.4–3.6 s | 1.9–2.0 s | 2.0 s |
| baked, cold | 3.0–3.1 s | 1.8–1.9 s | 1.9 s |

| per row | dish, before | dish, after |
|---|---|---|
| crop | 0.70 ms | 0.24–0.25 ms |
| blobs-to-mask | 590 runs at 1.9 ms | 1 run |
| memo, held after the cold walk | 1799 MB | 634 MB |
| memo projection | 3.07 MB/row, 2.3 windows | 1.07 MB/row, 6.5 windows |

The cropped cold walk is 2.5 s against 3.4 uncropped, the quarter the first half's sums predicted,
and the memo holds a third of what it did, the window fitting six times over against four and a
half uncropped, since the cut planes are a third the size. The walks that pay only the downstream
tools did not move, as they could not: nothing in either change touches a per-row tool. count read
the same 18.9 blobs a row.

## Seen on the way

A tool that raises at its first run ends the worker thread and leaves the walk waiting for a
progress event that never comes, the item the 2026-11-08 finding closed with; here a spliced node
without its DEFAULTS laid over its params did it, and `Document.resolve(tools)` after splicing is
what `load` does and the script now does. A run that looked hung was `grep` buffering a pipe; the
log is written line-buffered now.
