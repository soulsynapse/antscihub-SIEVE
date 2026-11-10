# Region and crop: drawn geometry as a table, a mask cut out of the frame, and a frame click that picks

Written 2026-11-09, from the design conversation of that day; no box is ticked. Read with the
registry's facet table and type report (`python -m sieve_player.registry`), the live statement of
what a tool may offer and what feeds what, with the root README's rule that a tool does one thing
and a variation is a second tool beside it, and with docs/spec/identity.md, whose Attach already
speaks of a region's blob on every ant inside it and whose Sample built membership from a region's
mask. docs/spec/bake.md names crop as the transform the bake is for and defers it here;
docs/spec/sources.md holds the fan-out this spec does not take, many rects of one plate under one
pipeline, which is a run over parameter sets and stays the processing run's.

## Why

On the purb document the ants stay inside a patch of the plate that could be drawn once, and every
tool after the decode touches the whole plane every row. docs/findings/2026-11-01-trex-runs-and-frame-parallel.md
put the cost where it is: the blobs pass went from 7.7 ms a row to 1.4 when it stopped touching the
plane and read inside each kept box, and nothing about that was decode. A crop buys that saving for
every plane-touching tool at once, blobs, morphology, background subtraction, flow, and a smaller
bake file, and it buys nothing on the decode, which bake.md settles is paid in full whatever is cut
afterwards. So a crop is worth having beside rescale and the bake, not instead of them, and it is
not what makes a cold window walk faster.

The word ROI covers three things, and the tree already treats two of them. A rect cut out of the
frame is a transform, plane in and smaller plane out. A region as membership, how many ants are in
the nest, is a mask and a column on each blob, which identity.md built: blobs-to-mask paints a
region, sample reads membership, attach writes the region onto the ants inside it. The same chain
on N equal boxes, six dishes on one plate, is neither; it wants N copies of the chain with N
outputs. Bonsai draws the first two lines where the tree does: Crop is one rect, CropPolygon is the
rect's box with the outside masked, RoiActivity takes a list of drawn polygons and emits one value
per region, so N lives in the output and never in the graph. Houdini keeps the loop over pieces
inside the SOP graph, where N is the data's and varies per row, which is what a blobs table is,
and puts the wedge over parameter sets outside the graph, in TOPs, where N is the user's; TRex,
idtracker.ai and DeepLabCut take one region or one crop per run and make the user run N times.
Nothing the player would copy puts N chain copies inside the graph, and this spec does not either:
N shapes in one file are N records in one table, and which of them the graph is looking at is one
param on one node.

The geometry is drawn outside the player. Drawing a polygon on a frame is a GUI mode the frame does
not have, and color_detector_v2 already set the pattern for a setting that is better tuned
elsewhere: a small JSON written by a dedicated utility, found beside the video by the `file`
selector, loaded into a node's params through `PATHS`, so that it is in the document and in the key.
A geometry file is strictly better than a painted mask for that role: it survives a rescale by
scaling, it edits, it can carry a name per shape, and once rasterized at plate size it is a mask of
the mask kind and goes through the same transforms the frame goes through, so no tool ever
reconciles coordinates. Circles, rotated squares and concave polygons are all one fill; a hole is
one region less another through combine.

Picking which shape the graph looks at is the one place the frame earns a click. The region node
draws its shapes on the frame as every table tool does, and a click on a shape is the most direct
way to say which one; the pane's list says the same thing more slowly. The click sets a param and
nothing else: which node the frame shows stays the display flag's, as a viewport click in Houdini
or Blender selects and never changes what the viewport displays, and the frame remembers where it
has been so a right click walks back.

## How to read this

Each `##` below is a deliverable: an `Assumes:` line naming what it builds on, a sentence of why,
then done-when assertions, each a box with a `Check:` that is a test in `tests/`. A box is ticked
by a session once its test passes in the tree; a session never unticks or rewrites an assertion,
and before building toward an unticked box checks whether the tree already meets it. Where a
result is worth Kendrick's eye before the next deliverable leans on it, a `Worth a look:` line says
what to look at; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:` are all
done is available; among those the earlier one in the file first. The branch is done when every
box is ticked.

Words. The *plate* is the frame the video node hands out, at its shape. A *geometry file* is what
the drawing utility writes: the plate's shape and a list of named *shapes*, each a polygon or a
circle in plate pixels. A *region* is the node that reads one and hands out its shapes as a table.
The *roi* of a crop is the mask it reads for its rect. To *pick* is to answer a click on the frame
with new params.

## Region

Assumes: nothing.

A table is the kind that already carries every downstream need: blobs-to-mask paints it, attach
and sample relate it to the animals, filter narrows it by a column, and identity.md's regions are
blobs already. A drawn shape is a record in every sense the kind has, a centroid, an area, a box
and a `contour` holding its vertices, so the region node produces blobs and no new kind.

Facts to weigh, as the tree stands at 705aa7dc and to be verified against it. tools/_table.py's
DTYPE has the position columns, the moment columns and `contour` as an object column, and
`with_column` adds a column of any dtype, so a shape's name can ride on the record; nothing in the
tree yet holds text in a table and the dtype's descr is what the writers serialize, so a name
column is the first text column the exports meet. tools/blobs_to_mask.py paints a record's contour
filled, so a circle is a contour sampled finely enough that its painted area is the circle's to
within a pixel ring. tools/file.py's card lists the matches with the picked one marked, clicking
one makes it the choice and clicking it again clears it, and the choice is a param; that is the
chooser this node wants, and the loader pattern is tools/inrange.py's `load_bounds`, which raises
on a malformed file with what was wrong. A `PATHS` loader answers params to merge, so the shapes
live in the node's params, JSON-able, and the key follows them. STATIC is read by the memo and the
monitor, so a node that is the same at every row says so and pays its raster once per key. A frame
carries no shape metadata, so the node learns the plate's shape from the frame it reads and can
only compare it to the file's; the two differing means the node is wired after a rescale or a crop,
and refusing with a standing that says so is the whole of coordinate handling, since the mask the
table paints goes through rescale and crop like any frame. A refusal is a raise, the tree's one way
for a run to say something about its node: the standing carries the two shapes and everything
downstream computes as None, as combine's two shapes do and as a Houdini SOP in error stops the
cook below it, rather than an empty table flowing on to fail two nodes later as a blank mask or an
empty roi. The second box's attach clause asks for the region's name on the ant inside it, and attach
joins the other way: a mark's centroid in a record's contour, so attach(region, ants) counts the ants in
the region and no argument order names the ant. Blender's Sample Nearest and Houdini's Attribute
Transfer and Group by Bounding Object each fix a join's direction by input order and treat the two
containment questions as two nodes, so the ant's side is the tool of Inside below, and the clause is
met there. Decided 2026-11-09.

- [x] A frame tool, a frame of any plane kind in for its shape, blobs out, STATIC, with a path
  input whose loader reads a geometry file into its params: the plate's shape and its shapes,
  each named, a polygon as its vertices or a circle as its centre and radius, in plate pixels. A
  file with any other geometry, a shape outside the plate, a repeated name or a malformed one
  raises with what was wrong.
  Check: a test loads a file of one polygon and one circle and reads the params; tests load a
  file with a triangle named twice, one with a shape past the plate's edge and one of another
  geometry, and read the reason in each exception.
- [x] Its table has one record per shape, the plane the frame's shape, the record's position and
  moment columns those of the filled shape and its contour the shape's outline, with the shape's
  name on the record; blobs-to-mask of the table paints the shapes, a circle's area within a
  one-pixel ring of πr², and attach, sample and filter read the table unchanged.
  Check: a test builds a region over a frame and compares the painted mask of a rotated square to
  its fill and a circle's painted area to πr²; a test attaches the region to a blobs table of two
  points, one inside, and reads the name on the inside one and NaN on the other.
- [x] A `choice` param, empty for every shape or a name for one, narrows the table to that record;
  the card lists the names with the chosen one marked, clicking a name chooses it and clicking it
  again clears it, as the file selector's card does; a name no longer in the file is treated as
  empty and the card says so.
  Check: a test sets choice to a name and reads one record, clears it and reads all, and sets a
  name the file lacks and reads all with the standing's line.
- [x] A frame of another shape than the file's plate gives no records and a standing saying which
  two shapes disagreed, so a region wired after a rescale or a crop is seen and never silently
  scaled.
  Check: a test wires the region after a rescale and reads the empty table and the standing.

Worth a look: a geometry file drawn by the utility over the crossings clip's first frame, around the
nest, loaded into a region on the purb document, its shapes drawn on the frame and the mask painted
from it; whether the drawn outline sits where it was drawn is the one thing a test cannot say.

## Inside

Assumes: Region.

Which region an ant is in is a column on the ant, feeding track, transitions and the csv, where a
count of ants on the region feeds a signal; attach gives the count, and this gives the label, with
the join's direction fixed by input order as Blender's Sample nodes and Houdini's Attribute Transfer
fix theirs.

Facts to weigh, to be verified. tools/attach.py relates two tables through `footprint`, scaling
by the ratio of the planes when they differ, and raises on a text column; `name` is the first text
column a tool meets, and where a record is in no region the column needs a value that is not a
number. An ant inside two overlapping regions is in the more specific one, the smaller by area,
where attach picks the largest mark.

- [x] A frame tool, blobs in and a second blobs table on `regions`, the first table out with the
  columns named in the params written onto each record whose centroid lies in a region's filled
  contour, or box by a knob, under a prefix the params give, `name` among them when the regions
  carry it: a record in no region reads NaN in a numeric column and None in a text one, and one in
  several reads the smallest by area; planes of two shapes relate in the first table's coordinates.
  Check: a test puts two points to a region table of a nest and a dish inside a larger yard and
  reads the nest's name on the point in both, None on the point in neither, and the count of
  regions each is in.

## A mask applied to a frame

Assumes: nothing.

Letting a frame through a mask is its own node reading both, by the README's rule, and it is what
makes region's mask a masking of the frame rather than a knob on crop or on threshold.

- [x] A frame tool, a frame of any plane kind in and a mask on a second input, out as in, every
  pixel the mask is zero at zeroed and every other pixel as it was; two shapes raise, as combine's
  do, and the node reports it.
  Check: a test masks a BGR frame and a gray frame against a mask with a hole and reads the hole
  zero and the rest equal; a test wires a mask of another shape and reads the standing.

## Crop

Assumes: nothing.

The rect is read off a mask so that a drawn region, a thresholded background and a union of
detections are all one tool's input, and the mask kind crops too so that the roi can follow the
frame it cut.

Facts to weigh, as the tree stands at 705aa7dc and to be verified against it. The window stack and
a table's plane both assume one shape per node under one key, so a crop's rect cannot follow a
mask that changes per row; STATIC was declared per tool and not propagated through a chain, so a
region through a combine was static in fact and not in declaration, and the plan could not tell
the crop whether its roi would hold still (since 2026-11-09 the plan inherits static through a
frame node fed only by static nodes, as Houdini propagates time dependence through a SOP chain, and
docs/findings/2026-11-09-crop-cold-walk.md says why; the crop's design below does not lean on it
either way). A rect that is a function of the roi at one fixed row is the
same for every row by construction, needs no propagation and holds no state, and for a static roi
it is the rect at every row anyway. A table found in a cropped frame has its columns in the crop's
pixels; draw paints in the displayed frame's pixels and the exports write the columns as they are,
so neither reads the table's plane, and only sample, attach and blobs-to-mask relate a table to a
plane of another shape, by the ratio of the shapes, which is right for a rescale and wrong for a
crop; the shapes alone cannot say which the user did. The plate offset a crop applies is a
function of its params and its roi, which is where an export could find it later, and the bake
knows nothing upstream of itself by design, so the sidecar is not where it lands.

- [x] A frame tool, a frame of any plane kind in and a mask on a second input named for the roi,
  out as in: the frame cut to the bounding box of the roi's nonzero pixels at the first row of the
  node's row space, grown by a `border` in pixels and clipped to the frame; the cut is the same at
  every row under one key, and a roi with no nonzero pixel gives nothing with a standing that says
  so.
  Check: a test crops a frame against a mask with one blob and reads the cut's shape, offset and
  pixels against the frame; a test with a border past the frame's edge reads the clipped cut; a
  test whose roi differs between row 0 and row 5 reads the same cut at both; a test with an empty
  roi reads the standing.
- [x] A mask cropped against itself as roi is the roi's own cut, so the frame and the mask that
  bounded it crop to one shape and meet downstream.
  Check: a test crops a frame and the same mask against that mask and reads equal shapes and the
  mask's nonzero pixels inside the cut.
- [x] A crop with the display flag shows the cut frame at its own shape, the row space unchanged,
  and the plan lists it as a frame node with its standing; a bake after a crop writes the cut
  frames and reads back at the cut's shape.
  Check: a test displays a crop offscreen and reads the shown frame's shape; a test bakes a
  cropped gray chain and reads the sidecar's shape and a served row's shape.

Worth a look: the crossings document with a region around the nest and the blobs chain after a
crop, cold walk and rewalk through `sieve_player/dev/monitor.py`, beside the uncropped figures in
docs/findings/2026-11-08-bake-window-fit.md, as a finding of its own; it is the claim the Why
rests on and the one number that says whether the branch did what it was for. Measured 2026-11-09 in
docs/findings/2026-11-09-crop-cold-walk.md; the eye's part, the drawn outline on the frame, is still open.

## Background folds a mask

Assumes: nothing.

The derived roi, everywhere the animals were ever seen, is the union of a detection mask over the
clip, and the tree's static union over sampled rows is background with `max`; it wants only to
accept the mask kind.

- [x] background accepts a mask and hands out a mask: `max` over its samples is their union and
  `min` their intersection, and `mean` and `median` on a mask are what they are on gray, so a
  thresholded chain into background into crop is the derived region with no new tool.
  Check: a test runs background with max over a mask that is nonzero in a different corner at
  each sampled row and reads every corner set; the registry's type report lists background as
  expecting mask.

## A click on the frame picks

Assumes: Region.

A node that draws on the frame may answer a click on it, and the answer is new params, so the
frame becomes a chooser for whatever a tool draws without the player learning what any shape is.

Facts to weigh, as the tree stands at 705aa7dc and to be verified against it. The display in
sieve_player/window.py holds `drawers`, every node whose tool has draw, and pulls each one's
result at the shown row into `frame_results` before painting, so the result a pick would read is
already at hand; a table node with the flag shows the nearest image upstream with its own draw over
it, so a region with the display flag shows the plate with its shapes drawn. The display has no
mouse handling. The pane applies a card's change to the document and emits that the node's params
changed, and the window re-keys from that; a pick lands the same way. draw receives the row, the
result, the start and the params and paints in the displayed frame's pixels; a pick receives the
same, with the point in those pixels, and a shape drawn over a frame of another shape than its
plane is wrong on that frame, which is an existing property of every drawer and not this spec's to
fix, so a pick on such a frame answers nothing. A draw that raises is dropped for the session, and
a pick is treated the same.

- [x] The registry's facet table lists a pick facet with its hint line: given the point in the
  displayed frame's pixels, the row, the node's result and its params, a tool answers the params
  to merge, or None for a click it does not claim; the registry's check does not call it.
  Check: a test reads the facet from the table and the hint.
- [x] A left click on the frame is offered to the drawing nodes whose results are on it, the one
  drawn last first, and the first that answers has its params merged through the document as a
  card's change is, so the key, the pane and the frame follow; a click no node claims does nothing,
  and a pick that raises is dropped for the session as a draw is, the line in the node's standing.
  Check: an offscreen test with two drawers, one that answers and one that does not, clicks and
  reads the document's params and the pane's card; a test with a pick that raises reads the
  standing and that the next click reaches the other drawer.
- [x] region picks: a click inside one of its shapes on a frame of its plane's shape makes that
  shape the choice, a click inside the chosen shape clears it, a click inside none or on a frame
  of another shape answers nothing; its draw marks the chosen shape apart from the rest.
  Check: a test picks at a point inside a shape and reads the choice, picks it again and reads it
  cleared, picks outside and reads None, and picks on a frame of half the shape and reads None.

## The display remembers

Assumes: nothing.

Looking at a dish means moving the display flag to the crop and coming back to the plate to pick the
next, so the frame keeps where it has been and a right click walks back; it knows nothing of crops.

- [x] A right click on the frame moves the display flag to the node it showed before the current
  one, and again to the one before that; the memory is the document's session, cleared when a
  document loads, a node gone from the document is skipped, and with nothing before there is
  nothing to do.
  Check: an offscreen test moves the flag across three nodes, right-clicks twice and reads the
  flag on the first; deletes the middle node, moves forward and back, and reads the middle
  skipped.

## Non-goals

- N copies of the chain for N shapes, or N traces in the timeline. A file of six dishes is six
  records and one choice; comparing dishes is a plot over the exported tables, which the
  processing run produces, and sources.md holds the run. Decided 2026-11-09.
- A click that moves the display flag, to the crop a region feeds or anywhere. Picking changes a
  param and the display flag changes what is shown; the first DCC convention is that a viewport
  click never does the second. Decided 2026-11-09.
- Drawing shapes in the player. The geometry file is written by a utility of its own, as
  color_detector_v2 writes inrange's bounds, and the player reads it. Decided 2026-11-09.
- The region scaling its geometry to a frame of another shape. The mask it paints goes through
  rescale and crop like any frame; a region wired past either is refused and says so.
- A crop whose rect follows the roi row by row. That is a tracking box, a different tool, and it
  breaks the one shape per key the stack and the tables rest on.
- Placing a table found in a cropped frame back on the plate, in the graph or in the sidecar. A
  table is in its frame's pixels, as a step reads rows and not seconds; the offset is the crop's
  and an export's to add when one wants it.
- A knob on crop choosing the row its rect is read at. The first row is the rule; a static roi
  makes the row moot and the derived roi is static.
- A hole as a primitive of the geometry file. An annulus is one region less another through
  combine.
- A knob on crop or on threshold that applies the mask. The mask tool is that.

## Open

- Whether the plate offset of a cropped table is written anywhere, for an export that wants plate
  coordinates. It is a function of the crop's params and roi; where an export reads it from waits
  on the first export that asks.
- A shortcut that cycles region's choice without the frame, once clicking has been used enough to
  say it is slow.
- Whether a pick may carry the display flag to the node that consumes the region's mask when
  exactly one does. Held until the two-click version has been lived with.
- ~~When a `PATHS` loader re-reads a changed file~~: settled 2026-11-09 by be59a820, on a change
  to the file. The window remembers the path and mtime it last handed each loader, watches every
  taken file, and re-asks the loaders once the writes settle; the settle time and the memory live
  in sieve_player/window.py. A reopen reads afresh; whatever repicks the path, the selector's
  rescan among them, runs the loader only when the path or its mtime moved.
- A drawer's shapes painted on a frame of another shape than its plane, which every table tool
  does today when the display flag is upstream or downstream of a rescale. A pick refuses such a
  frame; whether a draw should is its own question.
- Whether the first text column in a table, the shape's name, reads back through the table
  writers and the csv exports, or whether the name stays the record's and the exports carry an
  index. Decided by the first bake of a region or an export of an attached table.
