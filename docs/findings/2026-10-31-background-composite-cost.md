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
