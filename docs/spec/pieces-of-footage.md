# A cut in time, and the record every cut keeps

Read with `VISION.md`, whose picture this holds the tree to; with `tools/region.py`, the cut in
space; with `sieve_player/plan.py`, `sieve_player/walk.py` and `sieve_player/held.py`, which
plan, walk and hold what a cut reads; and with `docs/spec/what-a-node-declares.md`, whose keys
this assumes. What a table written below a cut holds is `docs/spec/what-leaves-the-player.md`'s.

## How to read this

As `docs/spec/monitor.md`'s How to read this. The sections are in the order they build: each
assumes only sections above it, and each box's check runs on what the sections above it built.

## Why

A pipeline picks the periods of the footage worth a closer look, and a heavier one runs inside
one of them, as a heavier one runs inside a region. Whatever is found there is the footage's: its
rows and pixels are the footage's, and it lays back over the footage beside what was found
around it.

## The model

A piece is a subset of one footage's pixels and rows, with a reference to each piece it was cut
from: one for a cut, two for an intersection, so pieces form a directed acyclic graph and not a
tree. Its extent is held on the footage, so lifting it back reads no parent. A region is a shape
over every row, a period every pixel over an unbroken run of rows, a region in a period both, and
a track a shape a row over a period. A piece of a piece is the intersection of the two. A cut
restricts and never renumbers: a row and a place below a cut are the footage's.

A node's extent follows the wires: it is its inputs' intersection, cut where a cutting node cuts,
and a node no cutting node feeds is of the whole footage whatever else the document cuts. Outside
its extent a node has no rows. They are absent to what reads it, never zero, a zero being a
measurement no row made.

Three things answer for a value at a row, and each is held apart: the recipe, which the key holds;
the row, the footage's; and, for a value made by a walk, the row the walk began at, its origin. A
value read from rows a bounded distance away, its reach, is the same at any two origins from that
many rows past the later. A value that depends on its origin is of its origin: the same rows
walked from two origins are two results under one recipe, told apart by origin and never by
which was held first. A thing named the same whether or not the footage was cut is of the first
kind; one of the second is named by its piece and origin as well. Whether a node steps, and not
whether it hands out a frame or a series, makes it of its origin: a frame tool that keeps state, a
motion history image, is of its origin as a series tool is.

A piece is what the user cut and no more. A node inside it reads the rows of its extent alone: a
row outside it is absent to that node as a row before the footage's first is, and no node widens
a piece by its own reach. The window is a view and not a cut, and alone reads before its first
row. A row of a result is addressed by its piece and its footage row, so two pieces whose extents
overlap each report the rows they share, and folding them back up keeps both and merges neither.

## Referents

What each settled, and the box it bears on. A session building a box reads its referent first.

- Nuke's NDK, `_validate`, `_request` and `engine`: an op's output box apart from the box asked of
  it, the ask passed upstream and grown by each op that reads past it, the hash not holding the
  ask. Rows below a cut are the footage's; the window's pre-roll.
- OpenFX's `getRegionOfDefinition`, `getRegionsOfInterest` and `getFramesNeeded`: the same split as
  a standard, the first carried forward along the wires and the last the rows an output row reads.
  A node's extent follows the wires; a frame read outside a piece.
- Halide (Ragan-Kelley and others, PLDI 2013): each stage's needed input inferred from the output
  asked of it, never set by hand. A tool's reach in rows, the window's pre-roll inferred.
- The Dataflow Model (Akidau and others, VLDB 2015): event time apart from processing time, and
  the session window, a period bounded by gaps. Rows below a cut are the footage's; A tool that
  cuts in time.
- Fading memory (Boyd and Chua, 1985): when a stateful operator forgets where it began, so a walk
  begun earlier converges on one walked alone, and only converges, so a fading memory is no
  bounded reach. A tool's reach in rows; A series result below a period.
- numpy's masked arrays and R's `NA`: absence carried through arithmetic and left out of a
  reduction, against a fill value a reduction counts. Outside a piece is absent.
- Overlap-save, and ghost cells in domain decomposition: a block computed over more than it keeps,
  the halo read and discarded. What a cut here refuses, a node widening its piece; what the window
  alone does.
- BED, GFF and bedtools: intervals half-open from 0 against closed from 1, the off-by-one between
  them, and intersect, merge and complement over periods, overlapping features each kept. A tool
  that cuts in time.
- CMX 3600 edit decision lists and conform: a cut's source in and out beside its record in and out,
  an offline cut relinked to the camera originals by source timecode. A piece's record.
- rasterio's windows and GDAL's geotransform: a window carrying its transform to the whole, windows
  of windows composed. A piece's record.
- Bazel's and Nix's hermeticity: a key holds all an action reads, and what is read and not held is
  how a cache goes stale. A stepped result is of its origin.
- ffmpeg's seeking, and H.264 and MPEG-TS: a seek that snaps to a keyframe under stream copy, a row
  decoded from the keyframe before it, a transport stream's timestamps that jump. A series result
  below a period's golden master, over `00000.MTS`.

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

## A tool's reach in rows

Assumes: nothing.

Facts to weigh. `travel` and `transitions` step a state that is the row before and nothing
earlier; `track`'s ids are of every row since its walk began. No tool says how far back its result
at a row reads, so the player can say of no two walks where they agree, nor how many rows before
the window's first a walk begins for its rows to be exact. The registry is the one reader of what
a tool declares (`docs/spec/what-a-node-declares.md`).

- [ ] A stepping tool declares its reach in rows, how far before a row its result there reads, or
  none, its reach unbounded; one left unsaid is unbounded, as is one whose memory fades and never
  ends.
  Check: `tests/test_registry.py`.
- [ ] A node's reach is its own added to that of the stepped nodes it reads, unbounded where any
  is. A walk begun at an earlier row stands in for one begun at a later at the rows the node's
  reach past the later, and at none before them.
  Check: a seam: `travel` walked from row 0 standing in for a walk from row 100 from row 101 on,
  and not at row 100; `track` at no row. And a one-off, each stepping tool walked from two origins
  over the crossings clip, the rows past the later at which they differ against its declared
  reach.

## A stepped result is of its origin

Assumes: A tool's reach in rows.

Facts to weigh. A held run (`held.Run`) holds the row it began at, and `held.py:Runs.over` serves
a range by cutting it from the run that began earliest whatever that row.
`window.py:PlayerWindow._ask_window` hands the window what `Runs.part` holds of the stepped nodes
and steps the rest from the window's first row, so a node stepped there reads, from a node handed
it, rows walked from an earlier row; the run that walk makes is held under the same keys as a walk
of the clip from row 0, with other values at the same rows, and the window shows whichever was
held first. None of this waits on a period.

- [ ] A held stepped result is addressed by its key, its origin and its rows, and a walk handed rows
  of one origin steps nothing of another from them. A run serves a range at the origin it is
  asked at, a period's first row or the window's, and one of another origin only as A tool's
  reach in rows allows.
  Check: a seam: `Runs.over` across the window walked from its own first row and the same rows cut
  from the clip's walk, two results under one key, each served at its own origin alone; and the
  window handed `track`'s rows of row 0 and stepping `count` from its own first row, refused.

## A tool that cuts in time

Assumes: A piece's record.

Facts to weigh. A series result's band is the rows under its gate (`graph.gated`), and the plot
washes them green for the selection alone (`plot.py`'s `theme.GATED`); the strip draws the
selection's gate over the clip (`timeline.py:envelope`). Periods read from a file on a path input
would set a range reaching nodes no wire joins to the `period`, the series node whose gate wrote
the file among them, by an edge no plan or key holds; a wire puts that edge in the plan, where a
series node below the `period` it feeds is a cycle (`plan.py`'s "in a cycle"). A period's first
row depends on the gate over rows before any window, so the gate over the window alone does not
say where a period that began before it begins. Not sized: what of `plan.py` lets a cutting frame
node read a series node's result on a wire.

- [ ] A `period` reads on a wire a series node's result over the whole clip, and its periods are
  the runs of rows the node's gate keeps, each the footage row it begins at and the row past its
  last, so periods that touch do not overlap. While no result of that node over the whole clip is
  held under the key it now has, the `period` has no periods and says it waits on that node's
  walk of the clip.
  Check: a one-off over the crossings clip: the periods against the gate's rows.
- [ ] A series node whose gate feeds a `period` is above it; one below it is a cycle, refused as
  one, saying both.
  Check: a seam.
- [ ] A `period` cuts the footage into its periods, each a piece of its own, however many its gate
  makes; none is chosen over another. Two `period`s in one document are each their own, fed by one
  series node's gate or two.
- [ ] The strip draws each `period`'s periods over the whole clip as spans in a colour of its own,
  so periods made by two gates show as two, whichever node is the selection.
  Check: a one-off offscreen: a document with two `period`s fed by two gates, the strip's spans
  against each gate's runs.

## A node's extent follows the wires

Assumes: A piece's record; A tool that cuts in time.

Facts to weigh. A walk is of one range, the window's or the clip's, and steps one chain
(`walk._Walk`, `chain_of`). `plan.plan` refuses a node whose inputs are of two pieces, the plate
among them; a served clip's pixels are H.264's and not the plate's, and a period's rows are the
footage's own. The tree sets the rows a document is walked over for a served clip alone. Not
sized: how far a node that serves no file and sets the rows of its extent reaches into `plan.py`
and `walk.py`. This section's boxes are one change to them.

- [ ] A node's extent is its inputs' intersection, cut where a cutting node cuts. What reads a
  `period` is walked over its periods' rows, each period alone, and a node no `period` feeds is
  walked over the rows it is walked over with none in the document.
  Check: a seam: a stepped node above a `period` and one below it, the one above's key and held
  rows the same with the periods moved, added and gone.
- [ ] The stepped nodes of one extent are walked together over it, and those of another apart over
  theirs.
  Check: a one-off over the crossings clip: `count` above a period and `track` below it, the rows
  each was stepped over.
- [ ] A period under a region and a region under a period both run, and their pieces have one
  extent.
  Check: a one-off over the crossings clip.
- [x] Kendrick: a node reading two pieces is refused, as today. A read across pieces, and a
  `lift` to an ancestor's extent, wait on a document that needs one.

## Rows below a cut are the footage's

Assumes: A node's extent follows the wires.

Facts to weigh. A frame node's value is kept by key and row (`graph.Graph._compute`). A stepped
tool's `step` is handed its row's place in the walk's range and not in the footage
(`walk._Walk.step`). A region's served clip is of the whole video's rows. `tools/motion.py:run`,
`tools/changeenergy.py` and `tools/flow.py` read `frames(row - 1)` and treat row 0 apart, so below
a period whose rows are the footage's each reads the row before the period's first.

- [ ] Every row a node below a period is handed, computes at, is held at and writes is the
  footage's.
  Check: a one-off over the crossings clip: a tracks csv below a period, its rows against the
  same node's above it.
- [ ] To what reads it by the row, a period's key is its input's: a node below a period that does
  not step has the key it has above, and computes no row held above. Neither the period's rows
  nor the result of the series node feeding it are in a key.
  Check: a seam: such a node below a period and one beside it, of one tool and params, one key.
- [ ] A frame read below a cut at a row outside the node's extent is absent, and a tool that reads
  a neighbouring row does at its extent's first row what it does at the footage's first, `motion`'s
  zero among them.
  Check: a seam: `motion` below a period at the period's first row against `motion` at row 0.
- [ ] Below a region, a row is the footage's as it is above it.
  Check: a one-off: a node's rows below a served region against the plate's.

## Outside a piece is absent

Assumes: A node's extent follows the wires.

Facts to weigh. `graph.gated` hands a series node downstream a gated-out row as a zero signal or
an empty table, so a sum, a mean or a count below it counts a row no one measured as a measured
zero, and an empty table reads as a row where nothing was found; `walk.py` is its one caller.
`walk._Walk.step` hands a stepping tool `None` where nothing feeds it. `plot.py:Plot.set_lines`
hands every line one start, where the strip takes one a node.

- [ ] A row outside a node's extent is absent to what reads it: no node is computed or stepped
  at it, and no table written holds a record of it.
  Check: a one-off over the crossings clip: a csv below a `period`, its rows against the periods'.
- [ ] A gated-out row is handed to a stepping tool downstream as absent, apart from a zero and
  from an empty table, and what a tool's state does across it is the tool's, each stepping tool
  saying so. Changes keys: it is said before it lands, and the held files of the documents in use
  are walked again, as `docs/spec/what-a-node-declares.md`'s Keys that move once.
  Check: a one-off over the crossings clip: `count` below a band, its result over a gated-out run
  against the same rows read as zero.
- [ ] The plot draws each node from the row its result begins at in the window, so a node below a
  `period` has a line over each of its periods' rows in the window, each from its own first row,
  and none between them; the frame shown at a row outside the shown node's extent says so in place
  of a frame.
  Check: a one-off offscreen: the window over several periods, a node below them, each line's
  first row and the frame at the row before one.

## A series result below a period

Assumes: Rows below a cut are the footage's; A stepped result is of its origin; Outside a piece is
absent.

Facts to weigh. A stepped node's result at a row depends on where its walk began; series in this
section's name is any node that steps, a frame tool that keeps state among them. The clip walk
and the window walk each step their chain from their own first row (`walk._Walk`). A gate can
make hundreds of periods over a clip, each its own origin. Not measured: the runs of as many
origins under `held.Runs`'s limit.

- [x] Kendrick: a stepped node's result below a `period` is each period walked alone, its
  origin the period's first row. It is the caveman way, the period cut to a clip of its own and
  the pipeline run on it, and so the ground truth; a walk cut from a longer one agrees with it
  only for a tool whose reach is bounded and declared, by A tool's reach in rows.
- [ ] A period's rows are in no key. A period moved, added or gone moves the extent of every node
  below its `period` and the origin of a stepped node's walk of it, and the walk of no other
  period.
  Check: a seam.
- [ ] A result below a period is the result of the same document run on the period cut to a
  lossless clip of its own, row for row and equal.
  Check: a one-off under `docs/findings/experiments/`, the golden master: each period of a
  `period` over the crossings clip cut by the player's decoder's rows to an RGB-lossless clip, its
  decoded rows checked byte for byte against the source's first; the document with its `period`
  taken out and its video the cut run on it; its tables, shifted by the period's first row,
  against those below the period, the rows that differ said.
- [x] Kendrick: the window is a walk of its own over its rows, its memory bounded as the window
  is, and never waits on its piece's walk, which an ancestor spanning most of the clip makes
  unbounded. A node whose reach is bounded is exact in it, walked from that reach before the
  window's first row; one whose reach is not is the window's best effort, and the window says so
  of its rows.
  Worth a look: how the window says it, which is Kendrick's to settle and not the building
  session's. A best-effort row is what the user expects of it: that a thing is tracked as the
  window moves, and not an identity's number, which only the whole clip walked gives. What the
  session builds toward it is conservative, reversible, predictable to the user, and quick
  without buying an unbounded walk.
- [ ] Below a `period`, the window walks each period it overlaps alone, a stepped node's walk of one
  begun at the later of that period's first row and the window's pre-roll, never before the
  period's first row. The periods of one `period` are disjoint, so the rows walked below it are
  at most the window's. A period that begins inside the window is exact below it, every node's
  reach bounded or not; best effort is of the period the window begins inside alone.
  Check: a one-off over the crossings clip: the window over several periods, `track` below them,
  each against its period walked alone.

## Not here

Walking every period, or every piece, with no window, and the tables it writes: the fourth of the
review's E2 (`docs/systems-review.md`), which has no spec yet; pieces that overlap fold back up by
the model's address there, both kept. A tool that makes a shape a row. Periods drawn by hand.
Periods of two results intersected. A margin grown or cut around a piece, or a halo read past
one, which change what the user cut. Region's key, which holds its cut, a served clip's pixels
being H.264's and not the cut's. A read across pieces, and a lift. Identity across pieces.
