# The background composite: what the first row costs, and what a row-invariant plane does to the memo

2026-10-31, on v5-blob-detection over 822199a8, with `tools/background.py` as first built. The file is
`Test video files/2025.7.17.1.59am_PRIVATE_M4ROOT_CLIP_30x_A5.mp4`, 592×602 at 30 fps, 169753 rows; the
graph video → gray → background, computed off the GUI through `Graph.compute`, one run each. Figures
are measurements except the 1080p column, which is arithmetic from the plane size.

## The first row

The composite is built inside the first `run()` that asks for it: `samples` rows spaced over the
clip, each a seek into the decoder, read through gray, then folded.

| stat | samples | first row | seeks | decodes | the next 20 rows |
|---|---|---|---|---|---|
| mean | 50 | 0.93 s | 49 | 98 | 0.000 s |
| mean | 100 | 1.96 s | 98 | 196 | 0.000 s |
| median | 50 | 1.24 s | 50 | 99 | 0.000 s |
| median | 100 | 2.29 s | 98 | 196 | 0.000 s |

About 20 ms a sample, two decodes a seek on this clip's GOP, and the fold is a small share of it
(median over mean adds 0.3 s at 100 samples). The cost is the seeks, so it scales with the sample
count and the clip's keyframe spacing, not with the plane: a 1080p clip of the same GOP pays about
the same first row plus a larger fold. It is paid again whenever the node's key changes, which
includes any knob upstream of it. Two seconds on the worker is a stall the scrub feels and the
monitor shows as one long run on the background node; it is not yet a reason to move the build
off the row path onto the clip walk's, and the knob to shorten it is `samples`.

## The memo under a row-invariant plane

`run()` returns the one composite object at every row, and the memo holds it under `(key, row)`
for each row visited, counting its bytes each time. After the first row and 20 more:

| | memo bytes | of which the composite's real footprint |
|---|---|---|
| 50 samples | 24.1 MB | 0.3 MB |
| 100 samples | 41.1 MB | 0.3 MB |

The rest is the sampled gray rows (50 × 0.34 MB) and 20 phantom entries of the composite (7 MB)
that share one allocation. The phantoms grow with every row scrubbed: at this clip's 0.34 MB a
row, 1500 rows visited fill a 512 MB memo on paper and evict every real plane in it; at 1080p
gray, 2 MB a row, 250 rows do. The memo's accounting is right for a plane that differs by row and
wrong for one that does not, and nothing in the tool's facets says which it is. Houdini's answer
is a time-dependence flag on the node: cooked once, cached once. The player has no such facet
yet; this is the figure that argues for one, and the fix is a player change, not the tool's.

## The same on 5.3K footage, and what the monitor made of it

Later the same day, over dfcb8ac0, on `video-tests/GX010047c2_02_17_26.MP4`, 5312×2988 at 23.98 fps,
11328 rows claimed and 11326 present, 45.4 MB a frame; the graph video → gray → background →
bg-subtract with bg-subtract reading gray on `in` and background on `bg`. The decoder measured a
step at 31 ms and a seek at 490 ms. The walk is `walk_row` plus a density per fed frame node, as
the worker runs it, over 30 rows; the scrub is the display asking for a row 3000 away every fifth
row, on its own cursor.

| | ms/row | of which video | bg-subtract | gray | the three densities |
|---|---|---|---|---|---|
| composite, 50 samples, median | 32500 once | 50 seeks | | | |
| walk alone | 45 | 34 | 6.0 | 1.5 | 2.4 |
| walk with scrubs | 85 | 73 | 6.6 | 2.0 | 2.5 |

So the clip is ten to twenty minutes of walk for eight minutes of footage, plus 30 s of composite
on every change upstream of the background node. The chain itself is within a 24 fps budget; the
decode is not, and the memo at 512 MB holds about ten rows of this chain (gray 16 MB, bg-subtract
16 MB, and 16 MB counted for the composite each row), so the window does not fit and the thrash
finding applies whole.

The monitor said 3 h for the clip. It takes each node's lifetime run ms over its runs as what a
cold row pays that node, and the background node has one run that is the whole composite, so
after 40 rows walked it reads 30 s / 40 ≈ 750 ms a row, times the clip's count. That figure is
the monitor's model, a run per row, applied to a node that runs once per key, and it is a second
consumer for the same row-invariance facet: with it the memo holds the plane once and the monitor
counts the build as a per-change cost and not a per-row one.

Two faults the clip surfaced, fixed over dfcb8ac0: the graph took the decoder's count at
construction, so the header's two phantom rows stayed in `frames.count` after the decoder had
corrected itself; it now reads the decoder's live. And the composite's last sample sits on the
claimed last row, so the tool stops at the first sample the clip lacks rather than failing.
