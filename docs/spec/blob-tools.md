# Blob tools: what the blob branch of the graph still lacks

Prospective, 2026-11-01, none built. Read with the registry's type report (`python -m
sieve_player.registry`), which is the live statement of what feeds what; at writing, `blobs` fed only
count, filter, size and track, `tracks` fed only travel, and nothing turned a table back into an
image, so a decision made on the table was lost to the image side of the graph. The order below is
the order the ants findings argue for (docs/findings/2026-11-01-ants-blob-features-and-linking.md,
docs/findings/2026-11-01-track-diagnostics.md): measure the linker before building on its ids,
then detection flickering at the area cut, tracks ending at a median of seven rows, the cluster
never resolving. Each tool is a module under tools/ with the facets the registry README names; a column is
a change to blobs.DTYPE and reaches filter for free. A tool lands only with a finding on the ants clip
that says what it changed, as blobs did.

## Measure first

The tracks filter and the export below presuppose ids that mean something, and
docs/findings/2026-11-01-track-diagnostics.md reads off the linker's own pass that on the purb
document nearly every contested assignment, absorption and teleport is the cluster, cut into
shifting fragments by split, and that the one linker defect the clip exposes was a lost track's reach
growing linearly with the gap. A √gap reach, an end-to-start stitch after the linker, and a bench of
linker variants (merge and split gates on area, a max_step calibrated from confirmed steps) were
tried the same day and dropped: each was tuned against one clip's self-reported counts or a
simulation built to the same assumptions, and none could be justified without ground truth. The
linker stays as it is. Still open: the cluster as a region rather than blobs, which is a settings
choice (split off, max_area) with blobs-to-mask, below, as the region's mask; and a labelled segment to settle the
swaps no self-report can count, which docs/spec/identity.md takes up with marks and codes as the
observations, scored as identity switches and IDF1 (Bernardin and Stiefelhagen's CLEAR MOT; Ristani et al.; Luiten et al.'s HOTA), which
`motmetrics` computes from two tables of row, id, x, y. The labels come from correcting the
tracker's own output on a clip of a few hundred rows, not from annotating frames, which needs the
tracks export (built, below) and a label mode in the GUI that records a human id per track id over a
row span.

What the literature says the structure should be, once that is in hand: every markerless system
that holds identity on insects (idTracker and idtracker.ai, Pérez-Escudero et al. 2014 and
Romero-Ferrero et al. 2019, the 2025 contrastive rewrite by Torrents, Costa and de Polavieja; TRex,
Walter and Couzin 2021; anTraX, Gal, Saragosti and Kronauer 2020, which is tags plus the same graph)
links only where it is unambiguous, cuts tracklets at every contact, and assigns identity to
single-animal tracklets afterwards, by appearance where the animals are large enough and by
propagation through the tracklet graph where they are not. None assigns through a crossing. The
wasp benchmark (WaspMOT, Stanczyk et al. 2026) finds motion-only trackers fragment even on perfect
detections, that appearance adds nothing for small identical insects, and that a spatial stitch of
tracklet ends to starts under a one-to-one assignment improves every tracker it tried, which is the
cheap half of the tracklet graph and the natural next step for the linker here. Dense colonies are
done with tags (Mersch, Crespi and Keller 2013; Crall et al. 2015; Wild et al. 2018; anTraX) or by
segmentation with learned correspondence (Bozek et al. 2021 on a bee comb), so the cluster is out of
reach of this pipeline's ids by design, not by tuning.

## A tracks filter (series; tracks in, tracks out)

The finding's open question is whether lowering min_area under the ants' distribution and letting the
linker carry an ant through its small rows mends the short tracks. It also lets speckle in, and the
remedy every tracker applies (trackpy's filter_stubs, TRex's track length cut, idtracker's fragment
minimum) is a cut on track-level properties afterwards: rows seen, net displacement, path length,
mean area, any of them bounded. filter reads one record at a time and cannot, so this is its own
tool, with filter's blank-is-none bounds. Ids are not renumbered; a dropped track's records leave the
table.

## Tracks to a file (series; tracks in, tracks out): built, tools/tracks_csv.py

Positions per id per row are what tracking is for; csv takes a signal, so this is its sibling,
sharing its Write widget and key line. Long format, one line per record, row, time, id, the blob
columns less contour, gate; a row with no records writes nothing. The signal is the records per
row, so the band gates by count.

## Morphology on the mask (frame; mask in, mask out)

Open and close, kernel size and iterations. Not a blob tool, and the fix for the flicker the finding
puts down to the area cut: an opening steadies an ant's area across rows and removes the one- and
two-pixel regions, over a hundred a row, before blobs counts them. Sits between threshold and blobs.

## Shape columns from the contour blobs already holds

`perimeter`, `hull` (convex hull area), `solidity` (area over hull) and `extent` (area over box
area). Solidity is the classic separator of one animal from two touching, a merged pair being
concave where a single ant is not, and it would tell the pile from the loose ants more honestly than
the diff-threshold split, which the finding shows returns nothing on the pile. The cost is a hull
per record over a few hundred points, which the per-record finding's figures say is noise.

## Blobs to a mask (frame; blobs in, mask out)

Built as tools/blobs_to_mask.py under docs/spec/identity.md: the kept records' contours or boxes painted
into a plane the shape the table carries, so a filtered table can gate flow, motion, bg-subtract or
reduce downstream.

## Kinematics on tracks (series; tracks in, tracks out)

`dx`, `dy`, `speed` and `heading` columns from an id's consecutive rows, NaN on a track's first row.
The moment `angle` is ambiguous by 180 degrees and motion resolves it; travel's moving threshold
and any speed cut in the tracks filter derive from these rather than each recomputing steps.

## Spacing (series; blobs in, signal out)

Nearest-neighbour distance between centroids, by a method, or the count of pairs within `r` px. For
ants it is the contact rate, the one behavioural number the branch cannot produce, and a pairwise
distance over a few records a row. A region filter is not needed: `cx` and `cy` are columns of
filter already.

## Held

Per-blob image patches (blobs and gray in, an image column out) are what posture, midline and
identity need, and nothing downstream wants them yet. An occupancy map over the walk is a series
tool with a frame output, a shape the graph's kinds do not have. Each waits for a consumer or a new
kind, and nothing in the finding is blocked on either.
