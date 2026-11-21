# A cut in time, and the record every cut keeps

Read with `VISION.md`, whose picture this holds the tree to; with `tools/region.py`, the cut in
space, which a cut in time mirrors; with `sieve_player/plan.py`, `sieve_player/walk.py` and
`sieve_player/held.py`, which plan, walk and hold what a cut reads; and with
`docs/spec/what-a-node-declares.md`, whose keys this assumes. What a table written below a cut
holds is `docs/spec/what-leaves-the-player.md`'s.

## How to read this

As `docs/spec/monitor.md`'s How to read this. The sections are in the order they build: each
assumes only sections above it, and each box's check runs on what the sections above it built.

Words. A *cut* is what a cutting node makes of the footage it reads: a region, a period, or one
inside another. A *cutting node* is the node that makes it, a `region` or a `period`. The tree's
name for a cut's record is `cut.Record`, and a node's are `plan.py:Entry.cuts`.

## Why

A pipeline picks the periods of the footage worth a closer look, and a heavier one runs inside
each of them, as a heavier one runs inside a region. Whatever is found there is the footage's: its
rows and pixels are the footage's, it is of the period it was found in and is nothing outside
one, and it lays back over the footage beside what was found around it.

## The model

A cut is a subset of one footage's pixels and rows, with a reference to each cut it was made
from: one where a node cut it, two for an intersection, so cuts form a directed acyclic graph and
not a tree. Made from is restriction and nothing else: a cut is a subset of every cut it was made
from. How tracks join and part, a merged tube of two tracks that is a subset of neither, is a
graph of its own over tracks and no edge of this one. A cut's extent is held on the footage, so
lifting it back reads no parent. A region is a shape over every row, a period every pixel over an
unbroken run of rows, a region in a period both, and a track a shape a row over a period. A cut of
a cut is the intersection of the two. A cut restricts and never renumbers: a row and a place below
a cut are the footage's.

A cut in time is a cut in space turned on its side. A `region` is fed its shapes by a file and
everything below it runs inside the region; a `period` is fed its periods, by a file or by a
gate, and everything below it runs inside each. What is computed inside a cut is what the
caveman way computes: the cut written to a clip of its own and the pipeline run on that clip.

A node's extent follows the wires: it is its inputs' intersection, cut where a cutting node cuts,
and a node no cutting node feeds is of the whole footage whatever else the document cuts. Outside
its extent a node has no rows. They are absent to what reads it, never zero, a zero being a
measurement no row made. A node inside a cut reads the rows of its extent alone: a row outside
it is absent to that node as a row before the footage's first is, and no node widens a cut by
what it reads. A node above a cutting node is of the footage it reads, so where a node sits says
which is wanted: `motion` above a `period` has at a period's first row the difference from the row
before it, and below it the zero it has at the footage's first.

Three things answer for a value: the recipe, which the key holds; the row, the footage's; and
what it read of the cut it was computed in. Each is held apart, and a value is of no more of its
cut than it read. `detect` in the middle of a period read its own frame and nothing of the
period, so it is the one value that key and row have above the period, below it and in any
period that holds the row, computed once. `motion` at a period's first row read that the period
begins there; `track` read where its walk began at every row; `background` read both ends. Below
a cut in space a value read the cut's shape at its row, which a region's key holds. So a period
whose edge moved moves the values that read that edge and no other, and a node's values in a
period are listed by the period's record whatever each read of it. Two periods that overlap each
report the rows they share, and folding them back up keeps both and merges neither. What names a
thing found below a cut is the cut's record with what the tool called it: a track's number is of
the period its walk was of, and the same number in two periods is two tracks.

A period's walk, every row of it from the first, is the result. The window is a view and not a
cut: it shows a period's walk where one is held, and where none is it walks its own rows as a
check that the pipeline works, which is no result and is held as none. What a node reads a
bounded count of rows away, its reach, the check walks and so has exactly; what reads back
without bound it has as best effort, and says so.

## Referents

What each settled, and the box it bears on. A session building a box reads its referent first.

- Nuke's NDK, `_validate`, `_request` and `engine`: an op's output box apart from the box asked of
  it, the hash not holding the ask. Rows below a cut are the footage's; the window a view.
- OpenFX's `getRegionOfDefinition`, `getRegionsOfInterest` and `getFramesNeeded`: the same split as
  a standard, the first carried forward along the wires and the last the rows an output row reads.
  A node's extent follows the wires; a frame read outside a cut.
- Houdini's TOPs, as `docs/systems-review.md`'s E2 reads it: a work item carrying its attributes
  to the items made from it, a node fanning out an item a cut, and a partition that waits on
  every item of a group. A value is of what it read; a read across a `period`'s periods.
- The Dataflow Model (Akidau and others, VLDB 2015): event time apart from processing time, the
  session window, a period bounded by gaps, and an aggregate a window. Rows below a cut are the
  footage's; A tool that cuts in time.
- Fading memory (Boyd and Chua, 1985): when a stateful operator forgets where it began, so a walk
  begun elsewhere converges on the period's own, and only converges, so a fading memory is no
  bounded reach. A tool's reach in rows; what the window's own walk is.
- Halide (Ragan-Kelley and others, PLDI 2013): each stage's needed input inferred from the output
  asked of it, never set by hand. A tool's reach in rows, what the window walks past its rows.
- numpy's masked arrays and R's `NA`: absence carried through arithmetic and left out of a
  reduction, against a fill value a reduction counts. Outside a cut is absent.
- Overlap-save, and ghost cells in domain decomposition: a block computed over more than it keeps,
  the halo read and discarded. What a cut here refuses, a node widening it.
- BED, GFF and bedtools: intervals half-open from 0 against closed from 1, the off-by-one between
  them, and intersect, merge and complement over periods, overlapping features each kept. A tool
  that cuts in time.
- CMX 3600 edit decision lists and conform: a cut's source in and out beside its record in and out,
  a cut list decided once and the heavy work conformed to it. A cut's record; a `period` fed by
  a file.
- rasterio's windows and GDAL's geotransform: a window carrying its transform to the whole, windows
  of windows composed. A cut's record.
- Bazel's and Nix's hermeticity: a key holds all an action reads, and what is read and not held is
  how a cache goes stale. A value is of what it read.
- anTraX (Gal, Saragosti and Kronauer, eLife 2020): tracklets a graph whose edges are blobs
  merging and splitting, identity passed along it, and no edge a containment. Made from is
  restriction; how tracks join and part is not here.
- Self-adjusting computation (Acar, 2005): an incremental result checked against the same
  computation run from scratch, from-scratch consistency the property that a stale value breaks. A
  period held not walked again.

## A cut's record

Assumes: nothing.

Facts to weigh. Two modules each compute a cut of their own. `plan.py:Entry.piece` is the id of
the nearest cutting node upstream, not an extent, and `graph.Graph._footage` walks those ids to
the file a node's frames are served from. `tools/region.py:origin` works out a frame's place on
the plate from its shape and the region's params. `region.py:run` refuses a frame that is not its
file's plate. The record replacing both is a contract change across `plan.py`, `graph.py` and
`region.py`, and not a value added beside them. A tool cuts, to the plan, by having a `cut_file`
(`registry.cuts`), so one that serves no file is no cutting tool; a tool is told the key of what
it reads (`frames.key`, `graph.Series`) and nothing of the cut it runs in.

- [x] A cut's record is one value: the footage it is of, the cuts it was made from, and its
  extent on the footage, a period of the footage's rows, a shape in the footage's pixels, or a
  shape a row over a period. Two records intersected are the record of the cut made from both,
  and a row or a place lifted through one is the footage's. What cut a node is of, the file its
  frames are served from, a place's origin on the plate, and a table's lift are that value's, and
  no module computes its own.
  Check: a seam: a region within a period and a period within a region have one extent, and a
  place lifted through either is the footage's.
- [x] The record holds a shape a row though no tool here makes one.
  Check: the same seam, a shape a row intersected with a period.
- [x] A tool cuts by saying its cuts: one declaration the registry reads answers the extent of
  each cut the node makes, from the node's params and, where its cuts are of a result it reads on
  a wire, from that result. `region` says its by it from a file's shapes, and `period` from a
  file's periods and from a gate, the gate's by the way a later tool whose cuts are a walk's
  result, a track's shapes among them, would say its own. A tool that cuts need write no file,
  and nothing in the player asks which tool a cutting node is.
  Check: `tests/test_registry.py`; and the record's seam through a tool made for the test that
  cuts by a result it reads and serves no file.
- [x] A tool is told the cut it runs in as it is told the key of what it reads: what hands it
  frames or a series answers that cut's record.
  Check: a seam: a tool below a region within a period, the record it is told against the
  record's own.

## A tool's reach in rows

Assumes: nothing.

Facts to weigh. `travel` and `transitions` step a state that is the row before and nothing
earlier; `track`'s ids are of every row since its walk began. `motion`, `changeenergy` and `flow`
do not step and read the row before; `smooth` runs whole and reads its `reach` rows either side;
`background` reads rows over its whole extent. No tool says how far from a row its result there
reads, so the player can say of no walk how many rows before the window's first it begins for its
rows to be exact, nor of a value below a cut whether it read the cut. The registry is the one
reader of what a tool declares
(`docs/spec/what-a-node-declares.md`).

- [x] A tool that reads a row other than the one it is asked at, one that steps, one that runs
  whole or one that reads a neighbouring frame, declares its reach in rows, how far before a row
  and how far after it its result there reads, or none, its reach unbounded; one left unsaid is
  unbounded, as is one whose memory fades and never ends and one that reads its whole extent.
  Check: `tests/test_registry.py`.
- [x] A node's reach is its own added to that of every node it reads, a frame node among them,
  unbounded where any is.
  Check: a seam: `travel` below `motion`, its reach the two added. And a one-off, each such tool
  walked from two first rows over the crossings clip, the rows past the later at which the two
  differ against its declared reach.

## A value is of what it read

Assumes: A cut's record; A tool's reach in rows.

Facts to weigh. A frame node's value is kept in the memo by key and row (`graph.Graph._compute`), a
static node's by key alone, and a held run's results by key (`held.good`). A held run (`held.Run`)
holds the row it began at and nothing of a cut, and `held.py:Runs.over` serves a range by cutting
it from the run that began earliest whatever that row; `Runs.hold` drops a run another covers
under the same keys. `window.py:PlayerWindow._ask_window` hands the window what `Runs.part` holds
of the stepped nodes and steps the rest from the window's first row, so a node stepped there
reads, from a node handed it, rows walked from an earlier row; the run that walk makes is held
under the same keys as a walk of the clip from row 0, with other values at the same rows, and the
window shows whichever was held first. `Runs` drops the oldest run past its limit. None of this
waits on a period: with no cutting node in the document a value is of the whole footage. Most
frame tools read the row they are asked at and no other (`tools/`), so most of what is computed
below a `period` read nothing of it.

- [x] Kendrick: a value is addressed by its key, its row and what it read of the cut it was
  computed in, the three held apart, and by nothing of the cut it did not read. A cut in time
  mirrors `region`, below which everything read the region's rect and is of it
  (`region.py:key_params`).
- [x] A value at a row further from the first and the last row of its node's extent than the
  node's reach before and after read nothing of the cut in time. It is held and served under its
  key and row alone, in the memo and in a held run: one value in every period that holds the
  row, computed once.
  Check: a seam: `detect` in two periods that overlap, one value a row and one computing of it.
- [x] A value within the node's reach of its extent's first row is of that row, and one within
  its reach of the last of that. A node whose reach before is unbounded is of its extent's first
  row at every row, and one that reads its whole extent of both. Under one key and row, two
  values that read two first rows, or two last, are two, and neither is served for the other.
  Changes the held file's form: it is said before it lands, and a held file of the form before it
  reads as none.
  Check: a seam: `motion` at one period's first row and the same key and row inside another
  period, two values, each served where it was read; `track` over the same rows from two first
  rows, two; a period's last row moved later, `track`'s rows before it standing and `smooth`'s
  within its reach of the old last row not.
- [x] A run is held with the row its walk began at and, where it reached it, the row its extent
  ended at, and serves a range a node at a time: a node's rows at any range further from the
  run's first row than the node's reach, and nearer only where the range's extent begins at that
  row. The window's own walk is held as the walk it was, and neither drops nor stands in for a
  run of another first row except so. A walk handed rows steps nothing from them that they do not
  so serve.
  Check: a seam: `Runs.over` across the window walked from its own first row and the same rows
  cut from the clip's walk, `travel`'s rows one past the window's first served by either and
  `track`'s by the clip's alone; and the window handed `track`'s rows of row 0 and stepping
  `count` from its own first row, refused.
- [x] A node's values in a cut are listed by the cut's record, whatever each read of it.
  Check: the same seam, two periods under one key listed, each record its own and the rows they
  share listed in both.

## A tool that cuts in time

Assumes: A cut's record.

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
period that began before it begins. What a `period` fed each way reaches into is sized in
`docs/findings/2026-11-20-held-runs-of-many-periods-and-what-a-period-reaches.md`.

Open: the file's form. Recommended, and a session may build on it: JSON as the geometry file is,
`{"rows": the footage's count, "periods": [{"name": ..., "first": ..., "end": ...}, ...]}`.

- [x] Kendrick: a `period` is fed as a `region` is, by a file the user fixed, and by a gate. The
  gate finds the periods; the file holds them still. Periods may overlap.
- [x] A `period` fed a file by a `file` selector has the file's periods, each the footage row it
  begins at and the row past its last, and a name. Periods of a file may touch and may overlap,
  each its own. A file that does not read, a repeated name, a period of no rows and one past the
  footage's rows are each refused, saying which. A save of the file reaches the `period` as a
  save of a geometry file reaches a `region`.
  Check: a one-off: a file of touching, overlapping and refused periods, the node's periods and
  what it says against the file.
- [x] A `period` fed a series node's result on a wire has the runs of rows that node's gate keeps
  over its whole extent, each the footage row it begins at and the row past its last, so periods
  that touch do not overlap, each named by its first row. While no walk of that node's extent is
  held under the key it now has, the `period` has no periods and says it waits on that node's
  walk.
  Check: a one-off over the crossings clip: the periods against the gate's rows.
- [x] A `period` fed both is refused, saying both. A series node whose gate feeds a `period` is
  above it; one below it is a cycle, refused as one, saying both.
  Check: a seam.
- [x] The periods a gate gave a `period` are written at the user's ask to a file of the file's
  form, and a `period` fed that file has the same periods.
  Check: a one-off over the crossings clip: a gate's periods written, read back and compared.
- [x] A `period` cuts the footage into its periods, each a cut of its own, however many it is
  fed; none is chosen over another. Two `period`s in one document are each their own.
- [x] The strip draws each `period`'s periods over the whole clip as spans in a colour of its own,
  so the periods of two `period`s show as two whichever node is the selection, and two periods of
  one that overlap show as two.
  Check: a one-off offscreen: a document with two `period`s, one fed a gate and one a file with an
  overlap, the strip's spans against each one's periods.

## A node's extent follows the wires

Assumes: A cut's record; A tool that cuts in time.

Facts to weigh. A walk is of one range, the window's or the clip's, and steps one chain
(`walk._Walk`, `chain_of`). `plan.plan` refuses a node whose inputs are of two cutting nodes, the
plate among them; a served clip's pixels are H.264's and not the plate's, and a period's rows are
the footage's own. `Entry` holds one key and one `piece` a node. The tree sets the rows a document
is walked over for a served clip alone. How far a node that serves no file, sets the rows of its
extent and is of a cut a period reaches into the player is sized in that finding, by module.
This section's boxes are one change to them.

- [x] A node's extent is its inputs' intersection, cut where a cutting node cuts. A node below a
  `period` is of each of its periods, under its one key. A node no `period` feeds is walked over
  the rows it is walked over with none in the document.
  Check: a seam: a stepped node above a `period` and one below it, the one above's key and held
  rows the same with the periods moved, added and gone.
- [x] The stepped nodes of one extent are walked together over it, and those of another apart over
  theirs.
  Check: a one-off over the crossings clip: `count` above a period and `track` below it, the rows
  each was stepped over.
- [x] A period under a region and a region under a period both run, and the two have one extent.
  A `period` under a `period` runs: the gate feeding the lower is read over the upper's periods,
  and each period it makes is a cut of the period it lies in.
  Check: a one-off over the crossings clip.
- [x] Kendrick: a node reading the cuts of two cutting nodes is refused, as today. A node reading
  every period of one `period`, a fold handing out a record a period with that period's extent,
  is not refused by this; it and a `lift` to an ancestor's extent wait on a document that needs
  one.

## Rows below a cut are the footage's

Assumes: A node's extent follows the wires; A value is of what it read.

Facts to weigh. A stepped tool's `step` is handed its row's place in the walk's range and not in
the footage (`walk._Walk.step`), and a tool that runs whole is handed the range's rows
(`walk.run_chain`). A region's served clip is of the whole video's rows. `tools/motion.py:run`,
`tools/changeenergy.py` and `tools/flow.py` read `frames(row - 1)` and treat row 0 apart, so below
a period whose rows are the footage's each reads the row before the period's first.
`tools/background.py` samples rows over `frames.count` and is held once a key. `tools/smooth.py`
reads the rows either side of each and takes the rows that exist at either end.

- [x] Every row a node below a period is handed, computes at, is held at and writes is the
  footage's.
  Check: a one-off over the crossings clip: a tracks csv below a period, its rows against the
  same node's above it.
- [x] Where a cut in time lies enters no recipe key: a node below a `period` has the key it has
  above it, and a value of it that read nothing of the period is the one above it, held and
  computed once, by A value is of what it read. A period moved, added or gone moves the values
  that read the edge that moved, and no key, no other period's and none that read no edge.
  Check: a seam: a node below a `period` and one beside it, of one tool and params, one key, and
  `detect`'s value at a row in the middle of a period computed once for the two; a period's first
  row moved, `detect`'s rows it still holds standing, `motion`'s at the old and the new first row
  not, and the other period's all standing.
- [x] A frame read below a cutting node at a row outside the node's extent is absent, and a tool
  that reads a neighbouring row does at its extent's first and last rows what it does at the
  footage's, `motion`'s zero and `smooth`'s shorter window among them.
  Check: a seam: `motion` below a period at the period's first row against `motion` at row 0, and
  above the period at that row the difference, the two held apart.
- [x] A node that reads its whole extent reads the period's rows and no other: the count of rows
  `background` samples over below a period is the period's, and it is held once a period.
  Check: a one-off over the crossings clip: `background` below a `period` of two periods, two
  composites, each against the composite of that period written to a clip.
- [x] Below a region, a row is the footage's as it is above it.
  Check: a one-off: a node's rows below a served region against the plate's.

## Outside a cut is absent

Assumes: A node's extent follows the wires.

Facts to weigh. `graph.gated` hands a series node downstream a gated-out row as a zero signal or
an empty table, so a sum, a mean or a count below it counts a row no one measured as a measured
zero, and an empty table reads as a row where nothing was found; `walk.py` is its one caller.
`walk._Walk.step` hands a stepping tool `None` where nothing feeds it. `smooth` reads the zeros,
by its own docstring.

- [x] A row outside a node's extent is absent to what reads it: no node is computed or stepped
  at it, and no table written holds a record of it.
  Check: a one-off over the crossings clip: a csv below a `period`, its rows against the periods'.
- [x] Kendrick: a gated-out signal row is handed as a masked array with NaN beneath, a signal
  of integers handed as floats; a table's row and a stepped row as None.
- [x] A gated-out row is handed to a tool downstream, one that steps or one that runs whole, as
  absent, apart from a zero and from an empty table, and what a tool does across it is the tool's,
  each such tool saying so. Changes keys: it is said before it lands, and the held files of the
  documents in use are walked again, as `docs/spec/what-a-node-declares.md`'s Keys that move once.
  Check: a one-off over the crossings clip: `count` below a band, its result over a gated-out run
  against the same rows read as zero.

## Every period walked

Assumes: Rows below a cut are the footage's; A value is of what it read; Outside a cut is
absent; A tool's reach in rows.

Facts to weigh. A stepped node's result at a row depends on where its walk began, and a node that
runs whole on where its range ends. The clip walk and the window walk each step their chain from
their own first row (`walk._Walk`), and the worker has a lane for each. A gate can make hundreds
of periods over a clip, each a walk of its own. `held.Runs` drops the oldest run past its limit,
and a walk closes at `walk.STACK_BYTES`. The runs of as many periods under that limit, and the
periods a band makes of a signal, are measured in that finding; a walk of many short ranges
against one of the same rows is not. The window walks and shows the chain of nodes no cut in time
feeds, so a node below a `period` draws no line there; `plot.py:Plot.set_lines` hands every line
one start, where the strip takes one a node.

- [x] Kendrick: a node's result below a `period` is each period walked alone, from the period's
  first row to its last. It is the caveman way, the period cut to a clip of its own and the
  pipeline run on it, and so the ground truth.
- [x] Kendrick: a period's walk has the results, and the window is a check that the pipeline
  works.
- [x] Kendrick: the window is a walk of its own over its rows, its memory bounded as the window
  is, and never waits on a period's walk, which a period spanning most of the clip makes
  unbounded. A node whose reach is bounded is exact in it, walked from that reach before the
  window's first row; one whose reach is not is the window's best effort, and the window says so
  of its rows.
- [x] The clip's walk below a `period` is a walk of each of its periods alone, and each is held as
  that period's. A table written below a `period` holds every period's rows, each said to be of
  its period.
  Check: a one-off over the crossings clip: the clip walked below a `period`, the rows stepped
  against the periods', and a tracks csv below it, its rows against the periods'.
- [ ] A period whose walk is held under the keys the chain now has is not walked again; one whose
  last row moved later is walked from where it ended, a node whose reach after is not none from
  that reach before; one whose first row moved is walked again for the nodes that read it; and a
  row two periods share is computed once for a node that read neither's edge. Every period's
  result so reached is the result of a walk of the same document from no store and no held run.
  Check: a one-off over the crossings clip, `motion` and `background` below the `period` beside
  `track`: a period moved and the clip walked again, the rows stepped that period's alone, and
  every period's result against a walk from no store and no held run, equal, the rows that differ
  said.
- [ ] Over a period whose walk is held the window shows that walk. Over one whose walk is not, it
  walks each period it overlaps alone, from the later of the period's first row and the window's
  first less the node's reach, to the earlier of the period's last and the window's last and the
  node's reach past it, and no row outside the period. A node whose reach is bounded is exact
  there, as is every node over a period that begins inside the window as far as its rows reach;
  best effort is of a node whose reach is not bounded, over the period the window begins inside
  alone, and the window says so of those rows. The rows of a period walked from its first row in
  the window are that period's walk as far as they reach.
  Worth a look: how the window says it, which is Kendrick's to settle and not the building
  session's. A best-effort row is what the user expects of it: that a thing is tracked as the
  window moves, and not an identity's number, which only the period's walk gives. What the
  session builds toward it is conservative, reversible, predictable to the user, and quick
  without buying an unbounded walk.
  Check: a one-off over the crossings clip: the window over several periods, `track` below them,
  held and not, each against its period walked alone and what the window says of each.
- [ ] The plot draws each node from the row its result begins at in the window, so a node below a
  `period` has a line over each of its periods' rows in the window, each from its own first row,
  none between them, and two where two periods overlap; the frame shown at a row outside the shown
  node's extent says so in place of a frame.
  Check: a one-off offscreen: the window over several periods, a node below them, each line's
  first row and the frame at the row before one.

## Not here

A walk with no window, over a folder or from a command: the rest of the review's E2
(`docs/systems-review.md`), which has no spec yet. A tool that reads every period of one
`period`. A tool that makes a shape a row. Periods drawn on the strip by hand. Two cuts
intersected by a node; two gates met on one signal above a `period` are that signal's gate. A
margin grown or taken off around a cut, or a halo read past one, which change what the user cut.
A period too short to keep and two a short gap parts, which are a tool's above the `period`.
A cut of a series result, a `period` on the chain. A period written to a clip and served in its
place, and the keys below one, as a `region`'s served clip has. Region's key, which holds its
rect, a served clip's pixels being H.264's and not the plate's. A lift. Identity across periods.
Each period cut to a lossless clip and the pipeline run on it, compared with the period's result:
beside a walk below the `period` of the period's rows alone, it checks only the decoder's
numbering of rows, which earns its cost over `00000.MTS`, its seeks snapping to keyframes and its timestamps
jumping, and not over a clip the player made.
