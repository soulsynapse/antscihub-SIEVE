# A cut in time, and the record every cut keeps

Read with `VISION.md`, whose picture this holds the tree to; with `tools/region.py`, the cut in
space, which a cut in time mirrors; with `sieve_player/plan.py`, `sieve_player/walk.py` and
`sieve_player/held.py`, which plan, walk and hold what a cut reads; and with
`docs/spec/what-a-node-declares.md`, whose keys this assumes. What a table written below a cut
holds is `docs/spec/what-leaves-the-player.md`'s.

## How to read this

As `docs/spec/monitor.md`'s How to read this. The sections are in the order they build: each
assumes only sections above it, and each box's check runs on what the sections above it built.

## Why

A pipeline picks the periods of the footage worth a closer look, and a heavier one runs inside
each of them, as a heavier one runs inside a region. Whatever is found there is the footage's: its
rows and pixels are the footage's, it is of the period it was found in and is nothing outside
one, and it lays back over the footage beside what was found around it.

## The model

A piece is a subset of one footage's pixels and rows, with a reference to each piece it was cut
from: one for a cut, two for an intersection, so pieces form a directed acyclic graph and not a
tree. Its extent is held on the footage, so lifting it back reads no parent. A region is a shape
over every row, a period every pixel over an unbroken run of rows, a region in a period both, and
a track a shape a row over a period. A piece of a piece is the intersection of the two. A cut
restricts and never renumbers: a row and a place below a cut are the footage's.

A cut in time is a cut in space turned on its side. A `region` is fed its shapes by a file and
everything below it is of the cut; a `period` is fed its periods, by a file or by a gate, and
everything below it is of the period. What is computed inside a piece is what the caveman way
computes: the piece cut to a clip of its own and the pipeline run on that clip.

A node's extent follows the wires: it is its inputs' intersection, cut where a cutting node cuts,
and a node no cutting node feeds is of the whole footage whatever else the document cuts. Outside
its extent a node has no rows. They are absent to what reads it, never zero, a zero being a
measurement no row made. A node inside a piece reads the rows of its extent alone: a row outside
it is absent to that node as a row before the footage's first is, and no node widens a piece by
what it reads. A node above a cut is of the footage it reads, so where a node sits says which is
wanted: `motion` above a `period` has at a period's first row the difference from the row before
it, and below it the zero it has at the footage's first.

Three things answer for a value: the recipe, which the key holds; the row, the footage's; and the
piece it was computed in. Each is held apart. One recipe at one row in two pieces is two values,
told apart by piece and never by which was held first, and a node's values are listed piece by
piece under its one key. A piece moved, added or gone moves the values of that piece and of no
other. Two pieces whose extents overlap each report the rows they share, and folding them back up
keeps both and merges neither.

A piece's walk, every row of its extent from the first, is the result. The window is a view and
not a cut: it shows a piece's walk where one is held, and where none is it walks its own rows as a
check that the pipeline works, which is no result and is held as none.

## Referents

What each settled, and the box it bears on. A session building a box reads its referent first.

- Nuke's NDK, `_validate`, `_request` and `engine`: an op's output box apart from the box asked of
  it, the hash not holding the ask. Rows below a cut are the footage's; the window a view.
- OpenFX's `getRegionOfDefinition`, `getRegionsOfInterest` and `getFramesNeeded`: the same split as
  a standard, the first carried forward along the wires and the last the rows an output row reads.
  A node's extent follows the wires; a frame read outside a piece.
- Houdini's TOPs, as `docs/systems-review.md`'s E2 reads it: a work item carrying its attributes
  to the items made from it, a node fanning out an item a piece, and a partition that waits on
  every item of a group. A value is of its piece; a read across the pieces of one cut.
- The Dataflow Model (Akidau and others, VLDB 2015): event time apart from processing time, the
  session window, a period bounded by gaps, and an aggregate a window. Rows below a cut are the
  footage's; A tool that cuts in time.
- Fading memory (Boyd and Chua, 1985): when a stateful operator forgets where it began, so a walk
  begun elsewhere converges on the piece's own, and only converges. What the window's own walk is.
- numpy's masked arrays and R's `NA`: absence carried through arithmetic and left out of a
  reduction, against a fill value a reduction counts. Outside a piece is absent.
- Overlap-save, and ghost cells in domain decomposition: a block computed over more than it keeps,
  the halo read and discarded. What a cut here refuses, a node widening its piece.
- BED, GFF and bedtools: intervals half-open from 0 against closed from 1, the off-by-one between
  them, and intersect, merge and complement over periods, overlapping features each kept. A tool
  that cuts in time.
- CMX 3600 edit decision lists and conform: a cut's source in and out beside its record in and out,
  a cut list decided once and the heavy work conformed to it. A piece's record; a `period` fed by
  a file.
- rasterio's windows and GDAL's geotransform: a window carrying its transform to the whole, windows
  of windows composed. A piece's record.
- Bazel's and Nix's hermeticity: a key holds all an action reads, and what is read and not held is
  how a cache goes stale. A value is of its piece.
- ffmpeg's seeking, and H.264 and MPEG-TS: a seek that snaps to a keyframe under stream copy, a row
  decoded from the keyframe before it, a transport stream's timestamps that jump. Every period
  walked's golden master, over `00000.MTS`.

## A piece's record

Assumes: nothing.

Facts to weigh. Two modules each compute a piece of their own. `plan.py:Entry.piece` is the id of
the nearest cutting node upstream, not an extent, and `graph.Graph._footage` walks those ids to
the file a node's frames are served from. `tools/region.py:origin` works out a frame's place on
the plate from its shape and the cut's params. `region.py:run` refuses a frame that is not its
file's plate. The record replacing both is a contract change across `plan.py`, `graph.py` and
`region.py`, and not a value added beside them.

- [ ] A piece's record is one value: the footage it is of, the pieces it was cut from, and its
  extent on the footage, a period of the footage's rows, a shape in the footage's pixels, or a
  shape a row over a period. Two records intersected are the record of the piece cut from both,
  and a row or a place lifted through one is the footage's. What a node's piece is, the file its
  frames are served from, a place's origin on the plate, and a table's lift are that value's, and
  no module computes its own.
  Check: a seam: a region within a period and a period within a region have one extent, and a
  place lifted through either is the footage's.
- [ ] The record holds a shape a row though no tool here makes one.
  Check: the same seam, a shape a row intersected with a period.

## A value is of its piece

Assumes: A piece's record.

Facts to weigh. A frame node's value is kept by key and row (`graph.Graph._compute`), a static
node's by key alone. A held run (`held.Run`) holds the row it began at and no piece, and
`held.py:Runs.over` serves a range by cutting it from the run that began earliest whatever that
row; `Runs.hold` drops a run another covers under the same keys. `window.py:PlayerWindow._ask_window`
hands the window what `Runs.part` holds of the stepped nodes and steps the rest from the window's
first row, so a node stepped there reads, from a node handed it, rows walked from an earlier row;
the run that walk makes is held under the same keys as a walk of the clip from row 0, with other
values at the same rows, and the window shows whichever was held first. `Runs` drops the oldest
run past its limit. None of this waits on a period: with no cut in the document the piece is the
plate over every row.

- [x] Kendrick: a value is addressed by its key, its piece and its row, the three held apart. A
  cut in time mirrors `region`, below which everything is of the cut (`region.py:key_params`).
- [ ] A value, a frame node's, a static node's or a series node's, is held and served under its
  key, its piece's record and its row. Under one key and row, two pieces hold two values, and
  neither is served for the other.
  Check: a seam: one key and row held in two pieces with two values, each served in its own.
- [ ] A run is a piece's walk when it began at the first row of that piece's extent, and is held
  as that piece's. The window's own walk from any other row is held as no piece's: it is never
  served as a piece's walk, and never drops or stands in for one. A walk handed rows of a piece's
  walk steps nothing from them that began at another row.
  Check: a seam: `Runs.over` across the window walked from its own first row and the same rows cut
  from the clip's walk, two results under one key, the clip's alone served as the plate's; and the
  window handed `track`'s rows of row 0 and stepping `count` from its own first row, refused.
- [ ] A node's held values are listed by piece under its key, each with its record.
  Check: the same seam, two pieces under one key listed, each record its own.

## A tool that cuts in time

Assumes: A piece's record.

Facts to weigh. A series result's band is the rows under its gate (`graph.gated`), and the band is
in no raw key (`plan.py`'s `key_of`), so a band moved moves a gate and no walk above it. The plot
washes the gate's rows green for the selection alone (`plot.py`'s `theme.GATED`); the strip draws
the selection's gate over the clip (`timeline.py:envelope`). A `region` is fed by a `file`
selector wired into `geometry`, loads and checks the file (`region.py:load_geometry`), and the
window's watch on the file reaches it on a save. A file of periods written by a node of the
document that reads it is an edge no plan or key holds; one the user fixed is a decided value, as
a geometry file is. A wire from a series node puts its edge in the plan, where a series node
below the `period` it feeds is a cycle (`plan.py`'s "in a cycle"). A period's first row depends
on the gate over rows before any window, so the gate over the window alone does not say where a
period that began before it begins. Not sized: what of `plan.py` lets a cutting frame node read a
series node's result on a wire.

Open: the file's form. Recommended, and a session may build on it: JSON as the geometry file is,
`{"rows": the footage's count, "periods": [{"name": ..., "first": ..., "end": ...}, ...]}`.

- [x] Kendrick: a `period` is fed as a `region` is, by a file the user fixed, and by a gate. The
  gate finds the periods; the file holds them still.
- [ ] A `period` fed a file by a `file` selector has the file's periods, each the footage row it
  begins at and the row past its last, and a name. Periods of a file may touch and may overlap,
  each a piece of its own. A file that does not read, a repeated name, a period of no rows and one
  past the footage's rows are each refused, saying which. A save of the file reaches the `period`
  as a save of a geometry file reaches a `region`.
  Check: a one-off: a file of touching, overlapping and refused periods, the node's periods and
  what it says against the file.
- [ ] A `period` fed a series node's result on a wire has the runs of rows that node's gate keeps
  over its whole extent, each the footage row it begins at and the row past its last, so periods
  that touch do not overlap, each named by its first row. While no walk of that node's extent is
  held under the key it now has, the `period` has no periods and says it waits on that node's
  walk.
  Check: a one-off over the crossings clip: the periods against the gate's rows.
- [ ] A `period` fed both is refused, saying both. A series node whose gate feeds a `period` is
  above it; one below it is a cycle, refused as one, saying both.
  Check: a seam.
- [ ] The periods a gate gave a `period` are written at the user's ask to a file of the file's
  form, and a `period` fed that file has the same periods.
  Check: a one-off over the crossings clip: a gate's periods written, read back and compared.
- [ ] A `period` cuts the footage into its periods, each a piece of its own, however many it is
  fed; none is chosen over another. Two `period`s in one document are each their own.
- [ ] The strip draws each `period`'s periods over the whole clip as spans in a colour of its own,
  so the periods of two `period`s show as two whichever node is the selection, and two periods of
  one that overlap show as two.
  Check: a one-off offscreen: a document with two `period`s, one fed a gate and one a file with an
  overlap, the strip's spans against each one's periods.

## A node's extent follows the wires

Assumes: A piece's record; A tool that cuts in time.

Facts to weigh. A walk is of one range, the window's or the clip's, and steps one chain
(`walk._Walk`, `chain_of`). `plan.plan` refuses a node whose inputs are of two pieces, the plate
among them, by the cutting node each is of; a served clip's pixels are H.264's and not the
plate's, and a period's rows are the footage's own. `Entry` holds one key and one piece a node.
The tree sets the rows a document is walked over for a served clip alone. Not sized: how far a
node that serves no file, sets the rows of its extent and has a piece a period reaches into
`plan.py` and `walk.py`. This section's boxes are one change to them.

- [ ] A node's extent is its inputs' intersection, cut where a cutting node cuts. A node below a
  `period` has a piece for each of its periods, under its one key. A node no `period` feeds is
  walked over the rows it is walked over with none in the document.
  Check: a seam: a stepped node above a `period` and one below it, the one above's key and held
  rows the same with the periods moved, added and gone.
- [ ] The stepped nodes of one extent are walked together over it, and those of another apart over
  theirs.
  Check: a one-off over the crossings clip: `count` above a period and `track` below it, the rows
  each was stepped over.
- [ ] A period under a region and a region under a period both run, and their pieces have one
  extent. A `period` under a `period` runs: the gate feeding the lower is read over the upper's
  periods, and each period it makes is a piece of the period it lies in.
  Check: a one-off over the crossings clip.
- [x] Kendrick: a node reading the pieces of two cuts is refused, as today. A node reading every
  piece of one cut, a fold over a `period`'s periods handing out a record a period with that
  period's extent, is not refused by this; it and a `lift` to an ancestor's extent wait on a
  document that needs one.

## Rows below a cut are the footage's

Assumes: A node's extent follows the wires; A value is of its piece.

Facts to weigh. A stepped tool's `step` is handed its row's place in the walk's range and not in
the footage (`walk._Walk.step`), and a tool that runs whole is handed the range's rows
(`walk.run_chain`). A region's served clip is of the whole video's rows. `tools/motion.py:run`,
`tools/changeenergy.py` and `tools/flow.py` read `frames(row - 1)` and treat row 0 apart, so below
a period whose rows are the footage's each reads the row before the period's first.
`tools/background.py` samples rows over `frames.count` and is held once a key. `tools/smooth.py`
reads the rows either side of each and takes the rows that exist at either end.

- [ ] Every row a node below a period is handed, computes at, is held at and writes is the
  footage's.
  Check: a one-off over the crossings clip: a tracks csv below a period, its rows against the
  same node's above it.
- [ ] A period's rows are in no key: a node below a `period` has the key it has above it, and its
  values there are of the period by A value is of its piece. A period moved, added or gone moves
  the values of its own piece below its `period`, and no key and no other piece's.
  Check: a seam: a node below a `period` and one beside it, of one tool and params, one key and
  two pieces; a period moved, the other period's values standing.
- [ ] A frame read below a cut at a row outside the node's extent is absent, and a tool that reads
  a neighbouring row does at its extent's first and last rows what it does at the footage's,
  `motion`'s zero and `smooth`'s shorter window among them.
  Check: a seam: `motion` below a period at the period's first row against `motion` at row 0, and
  above the period at that row the difference, the two held apart.
- [ ] A node that reads its whole extent reads the period's rows and no other: the count of rows
  `background` samples over below a period is the period's, and it is held once a piece.
  Check: a one-off over the crossings clip: `background` below a `period` of two periods, two
  composites, each against the composite of that period cut to a clip.
- [ ] Below a region, a row is the footage's as it is above it.
  Check: a one-off: a node's rows below a served region against the plate's.

## Outside a piece is absent

Assumes: A node's extent follows the wires.

Facts to weigh. `graph.gated` hands a series node downstream a gated-out row as a zero signal or
an empty table, so a sum, a mean or a count below it counts a row no one measured as a measured
zero, and an empty table reads as a row where nothing was found; `walk.py` is its one caller.
`walk._Walk.step` hands a stepping tool `None` where nothing feeds it. `smooth` reads the zeros,
by its own docstring. `plot.py:Plot.set_lines` hands every line one start, where the strip takes
one a node.

- [ ] A row outside a node's extent is absent to what reads it: no node is computed or stepped
  at it, and no table written holds a record of it.
  Check: a one-off over the crossings clip: a csv below a `period`, its rows against the periods'.
- [ ] A gated-out row is handed to a tool downstream, one that steps or one that runs whole, as
  absent, apart from a zero and from an empty table, and what a tool does across it is the tool's,
  each such tool saying so. Changes keys: it is said before it lands, and the held files of the
  documents in use are walked again, as `docs/spec/what-a-node-declares.md`'s Keys that move once.
  Check: a one-off over the crossings clip: `count` below a band, its result over a gated-out run
  against the same rows read as zero.
- [ ] The plot draws each node from the row its result begins at in the window, so a node below a
  `period` has a line over each of its periods' rows in the window, each from its own first row,
  none between them, and two where two periods overlap; the frame shown at a row outside the shown
  node's extent says so in place of a frame.
  Check: a one-off offscreen: the window over several periods, a node below them, each line's
  first row and the frame at the row before one.

## Every period walked

Assumes: Rows below a cut are the footage's; A value is of its piece; Outside a piece is absent.

Facts to weigh. A stepped node's result at a row depends on where its walk began, and a node that
runs whole on where its range ends. The clip walk and the window walk each step their chain from
their own first row (`walk._Walk`), and the worker has a lane for each. A gate can make hundreds
of periods over a clip, each a walk of its own. `held.Runs` drops the oldest run past its limit,
and a walk closes at `walk.STACK_BYTES`. Not measured: the runs of as many pieces under that
limit.

- [x] Kendrick: a node's result below a `period` is each period walked alone, from the period's
  first row to its last. It is the caveman way, the period cut to a clip of its own and the
  pipeline run on it, and so the ground truth.
- [x] Kendrick: the piece's walk has the results. The window is a check that the pipeline works,
  a walk of its own over its rows, its memory bounded as the window is, and it never waits on a
  piece's walk.
- [ ] The clip's walk below a `period` is a walk of each of its periods alone, and each is held as
  that period's. A period whose walk is held under the keys the chain now has is not walked
  again, and one moved, added or gone is walked or dropped alone. A table written below a
  `period` holds every period's rows, each said to be of its period.
  Check: a one-off over the crossings clip: the clip walked below a `period`, the rows stepped
  against the periods'; a period moved and the clip walked again, the rows stepped that period's
  alone.
- [ ] A result below a `period` is the result of the nodes below it run on the period cut to a
  lossless clip of its own, row for row and equal. A node above the `period` is of the footage
  and is not in the comparison.
  Check: a one-off under `docs/findings/experiments/`, the golden master: each period of a
  `period` over the crossings clip cut by the player's decoder's rows to an RGB-lossless clip, its
  decoded rows checked byte for byte against the source's first; a document of the nodes below
  the `period`, its video the cut, run on it; its tables, shifted by the period's first row,
  against those below the period, the rows that differ said.
- [ ] Over a period whose walk is held the window shows that walk. Over one whose walk is not, it
  walks from the later of the period's first row and its own, and no row before the period's
  first; what it shows of a walk that is not the period's it says is a check, and the rows of a
  period walked from its first row in the window are that period's walk as far as they reach.
  Worth a look: how the window says it, which is Kendrick's to settle and not the building
  session's. A check is what the user expects of it: that a thing is tracked as the window moves,
  and not an identity's number, which only the piece's walk gives. What the session builds toward
  it is conservative, reversible, predictable to the user, and quick without buying an unbounded
  walk.
  Check: a one-off over the crossings clip: the window over several periods, `track` below them,
  held and not, each against its period walked alone and what the window says of each.

## Not here

A walk with no window, over a folder or from a command: the rest of the review's E2
(`docs/systems-review.md`), which has no spec yet. A tool that reads every piece of one cut. A
tool that makes a shape a row. Periods drawn on the strip by hand. Periods of two results
intersected as pieces; two gates met on one signal above a `period` are that signal's gate. A
margin grown or cut around a piece, or a halo read past one, which change what the user cut. A
tool that says it reads its own row alone, so that its rows above a cut stand in below it. A
tool's reach in rows, so that a walk begun elsewhere stands in for a piece's. A cut of a series
result, a `period` on the chain. Region's key, which holds its cut, a served clip's pixels being
H.264's and not the cut's. A lift. Identity across pieces.
