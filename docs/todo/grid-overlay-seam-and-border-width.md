---
title: Grid overlay seam and border width
status: open
opened: 2026-07-27
gated_on: nothing structurally — both defects live in one paint routine
reads:
  - src/sieve/gui/composite_view.py
---

# Grid overlay: the heat seam, and 2 px borders that should be 1

Noticed 2026.07.27, both visible in one screenshot of
`rep3_intermittent_crop.MP4`, both in `CompositePane._paint_grid`
(`src/sieve/gui/composite_view.py:318`).

## The seam: a 1 px line of unblended footage across the heatmap

With heat on, a horizontal line crosses the pane — the footage showing through
a gap between heat rows, unblended, which against a warm-toned arena reads as
a painted yellow line. Two candidate causes, and the repro distinguishes them:

1. **Rounding between cell rectangles.** `cell_rect` derives each cell from
   float `g.width()/nx, g.height()/ny`; if fills land on device pixels
   independently per cell, adjacent rows can round apart by one pixel at
   certain pane heights. **Test: resize the pane by a pixel at a time — if the
   seam moves or vanishes, it is this.** Fix shape: compute each cell edge as
   the *rounded grid line position* (edge `i` at `round(g.top + i*h/ny)`) so
   neighbouring cells share an edge exactly, rather than each cell rounding
   its own origin and extent.
2. **Partial edge blocks.** `grid_shape` is ceiling division and partial
   blocks are real blocks, so the grid's *data* extent is `ny*block` working
   pixels — up to `block-1` px past the frame. If the paint maps `ny` cells
   onto the image rect uniformly, cells are drawn slightly too short and the
   error accumulates… but that mismatch distorts alignment everywhere rather
   than opening one clean gap, and the seam in the screenshot sits mid-pane,
   not at the crop edge. **Test: change block size — if the seam tracks a
   particular data row rather than a pane height, it is this.** (This mapping
   question is worth checking while in the file even if (1) is the seam:
   detection squares registered against the frame are a rule-6 concern.)

The screenshot's seam is most consistent with (1).

## The borders: adjacent detected cells double to 2 px

Each detected cell paints its own 1 px ring, so neighbouring detected cells
lay their rings side by side — 2 px walls inside a detected region, 1 px on
its outer boundary, which is backwards: the interior lines are the least
informative and get the heaviest ink. Wanted: 1 px everywhere.

Fix shape: stop drawing per-cell rects and stroke *edges* instead — an edge is
drawn once iff exactly one of the two cells it separates is detected (outer
boundary), or drawn once, not twice, when both are (shared wall) — whichever
read of "1 px" is wanted; the boundary-only version is the cleaner picture and
worth trying first. This also composes with the seam fix: edges live on the
same rounded grid lines the fill uses, so ring and interior stay the disjoint
pixel regions the module docstring already promises ("border alpha 0 reads as
separated blocks").

~30–60 lines, one file. Tests: two adjacent detected cells share one 1 px
edge (paint onto a QImage and count the stroked column's width); heat fills
tile with no uncovered row at any pane height in a sweep of heights (assert no
row of pure-background pixels inside the grid rect); a lone detected cell
still shows a full ring.
