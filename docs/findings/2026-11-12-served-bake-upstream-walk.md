# A served bake does not spare the window walk its upstream, and the monitor cannot say so

2026-11-12, on v5 at cce7cb8e, read off `sieve_player/dev/monitor.py` and the raw event stream, driving the
player's own Graph and Worker offscreen through
`docs/findings/experiments/2026-11-12-served-bake-upstream-walk.py`. The document is
`video-tests/purb-settings.json` on `00000.MTS`, 1920×1080 at 59.94 fps, 38100 rows: video → crop (roi from
region → blobs-to-mask) → rescale 1.0 → bake → threshold → blobs, with track, count, size and travel as the
chain. The bake is the one in the store under c926119b06011804, gray 274×203, standard quality, the whole
clip. Window 600 rows, the player's default limits, four runs of each fresh-graph phase and three of the
one-session pair; the question was Kendrick's, that the player read about 5.1× live and 4.2× baked where
loading a cropped file read 6×.

## The walks

| walk | wall, 600 rows | ms/row | realtime, measured | realtime, the monitor's cold line | plate decodes |
|---|---|---|---|---|---|
| fresh graph, live, cold | 1.39–1.50 s | 2.32–2.49 | 6.7–7.2× | 6.7–7.3× | 600 |
| fresh graph, baked, cold | 1.59–1.63 s | 2.65–2.72 | 6.1–6.3× | 6.5–6.6× | 600 |
| one session, live then switched to baked | 0.69–0.76 s | 1.14–1.26 | 13.3–14.6× | 6.2–6.9× | 0 |

Baked on a fresh graph is slower than live by the file's decode, and the plate is decoded at every row of
it. Switched to baked in a session whose memo holds the live walk, the plate is not touched, the walk is
twice as fast as live, and the monitor still reads the live figure.

## What a row pays

| per row, ms | live | baked, fresh | baked, after a live walk |
|---|---|---|---|
| video, the plate's decode | 1.05–1.13 | 1.05–1.07 | 0 |
| crop, run + fold | 0.23 + 0.05 | 0.26 + 0.04 | 0 |
| rescale, run + fold | 0.01 + 0.03 | 0.005 + 0.025 | 0 |
| bake: live run, or the file's decode, + fold | 0.01 + 0.03 | 0.22 + 0.03 | 0.22 + 0.03 |
| threshold, run + fold | 0.02 + 0.10 | 0.03 + 0.09 | 0.03 + 0.10 |
| blobs | 0.39–0.41 | 0.45 | 0.41 |
| chain, stepped and whole | 0.19 | 0.22 | 0.19 |
| unprobed | 0.22–0.26 | 0.24 | 0.18 |

The window walk folds a density for every fed frame node at every row (`_Walk.turn`, over
`Graph.frame_nodes()`), and a served bake cuts its own sources, not its upstream's standing: crop and
rescale are fed by the video whether or not anything reads them, so their folds pull the plate through the
decoder at every row. The served walk therefore pays the live walk and the file's decode on top, 0.22 ms.
In a session that walked live first, those folds are memo hits, so nothing upstream runs; that is the only
arrangement in which the bake's saving was ever seen, and it is the memo's, lost at the first eviction or
restart. The clip walk folds nothing (`densities` is None on it), so by the code a served clip walk reads
the file alone; not measured here.

What the bake buys this document once the upstream is not walked is the third column: 1.14 ms a row against
2.4, the plate's decode and the crop replaced by a fifth of a millisecond. The file's decode is a fifth of
the plate's for a thirty-seventh of the pixels, so on a plane this small the read is mostly the capture's
call, not the pixels.

## Why the monitor did not show it

Three separate things, each visible in the tables the script prints.

The cold line sums each node's latest walk it ran in, so after the switch it still adds video, crop and
rescale, which ran zero times: 6.9× on a walk that measured 14.6×. On a fresh graph the same sum is right
only because the walk really does run them. The projection has no notion of which nodes a cold row reaches
under the plan as it stands.

The read kinds are summed over every node that reads and printed on the video line: fresh and baked it says
`601 cache 1200 decode`, the plate's 600 decodes and the file's 600 as one figure. The bake line reads
1200 runs at 0.11 ms, the mean of 600 decodes at 0.22 and 600 cached reads at 0.003. The served reader's
store is not a lane, which the 2026-11-08 finding already asked for.

Nothing states that a node ran without a reader. crop's 600 runs under a served bake have no consumer but
their own fold, and the stream carries no fact that would let a reader of it tell that from a run blobs
needed.

## What this does to two earlier findings

`2026-11-08-bake-window-fit.md` and `2026-11-09-crop-cold-walk.md` both report a "baked, cold" walk that
left the plate decoder's counters still and came in under the live cold walk. Both scripts bake on the
graph they then walk, after live walks over the same window, so the memo held every upstream fold: their
"baked, cold" is this finding's third row, not its second. The read counts there are right for that
arrangement; "cold" overstates it.

## Not reproduced

The player's own figures were lower than these throughout, 5.1× live against 7.0× here, and a cropped file
loaded directly read 6× there where the third row here reads 14×. The offscreen run has no GUI taking its
turn: no plot, no frame paint, no clip walk behind the window. What the player adds per row is the
unprobed line's to say and was not measured.
