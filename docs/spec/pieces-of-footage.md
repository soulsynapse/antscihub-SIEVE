# A cut in time, and the record every cut keeps

Read with `VISION.md`, whose picture this holds the tree to; with `tools/region.py`, the cut in
space; with `sieve_player/plan.py`, `sieve_player/walk.py` and `sieve_player/held.py`, which
plan, walk and hold what a cut reads; and with `docs/spec/what-a-node-declares.md`, whose keys
this assumes. What a table written below a cut holds is `docs/spec/what-leaves-the-player.md`'s.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

## Why

A pipeline picks the periods of the footage worth a closer look, and a heavier one runs inside
one of them, as a heavier one runs inside a region. Whatever is found there is the footage's: its
rows and pixels are the footage's, and it lays back over the footage beside what was found
around it.

## The model

A piece is a subset of one footage's pixels and rows, with a reference to each piece it was cut
from: one for a cut, two for an intersection, so pieces form a directed acyclic graph and not a
tree. Its extent is held on the footage, so lifting it back reads no parent. A region is a shape over every row, a period every pixel over an unbroken run of rows, a region in
a period both, and a track a shape a row over a period. A piece of a piece is the intersection of
the two. A cut restricts and never renumbers: a row and a place below a cut are the footage's.

A node's extent follows the wires: it is its inputs' intersection, cut where a cutting node cuts,
and a node no cutting node feeds is of the whole footage whatever else the document cuts. Outside
its extent a node has no rows. They are absent to what reads it, never zero, a zero being a
measurement no row made.

Three things answer for a value at a row, and each is held apart: the recipe, which the key holds;
the row, the footage's; and, for a value made by a walk, the row the walk began at, its origin. A
value read from rows a bounded distance away, its reach, is the same at any origin once those rows
are read, the footage's rows outside the piece among them, and so the same whichever piece it is
computed in. A value that depends on its origin is of its origin: the same rows walked from two
origins are two results under one recipe, told apart by origin and never by which was held first.
A thing named the same whether or not the footage was cut is of the first kind; one of the second
is named by its piece and origin as well. Whether a node steps, and not whether it hands out a
frame or a series, makes it of its origin: a frame tool that keeps state, a motion history image,
is of its origin as a series tool is.

A piece owns the rows of its extent and may read more: the rows a reach reads past its edge, and
the rows a walk begun before its first row walks to arrive there. What it reads is its parent's;
what it reports is its extent's alone. A row of a result is addressed by its piece and its
footage row, so two pieces whose extents overlap each report the rows they share, and folding
them back up keeps both and merges neither.

## Referents

What each settled, and the box it bears on. A session building a box reads its referent first.

- Nuke's NDK, `_validate`, `_request` and `engine`: an op's output box apart from the box asked of
  it, the ask passed upstream and grown by each op that reads past it, the hash not holding the
  ask. Rows below a cut are the footage's; A tool that cuts in time's keys.
- OpenFX's `getRegionOfDefinition`, `getRegionsOfInterest` and `getFramesNeeded`: the same split as
  a standard, the first carried forward along the wires and the last the rows an output row reads.
  A node's extent follows the wires; a node that does not step reading a neighbouring row.
- Halide (Ragan-Kelley and others, PLDI 2013): each stage's needed input inferred from the output
  asked of it, never set by hand. Outside a piece is absent; A tool's reach in rows, the
  pre-roll inferred.
- The Dataflow Model (Akidau and others, VLDB 2015): event time apart from processing time, and
  the session window, a period bounded by gaps. Rows below a cut are the footage's; The periods
  a `period` chooses among.
- Fading memory (Boyd and Chua, 1985): when a stateful operator forgets where it began, so a walk
  begun earlier converges on one walked alone, and only converges, so a fading memory is no
  bounded reach. A series result below a period.
- numpy's masked arrays and R's `NA`: absence carried through arithmetic and left out of a
  reduction, against a fill value a reduction counts. Outside a piece is absent.
- Overlap-save, and ghost cells in domain decomposition: a block computed over more than it keeps,
  the halo read and discarded, so blocks that overlap in what they read are disjoint in what they
  report. The model's owned rows; a pre-roll.
- BED, GFF and bedtools: intervals half-open from 0 against closed from 1, the off-by-one between
  them, and intersect, merge and complement over periods, overlapping features each kept. The
  periods a `period` chooses among.
- CMX 3600 edit decision lists and conform: a cut's source in and out beside its record in and out,
  an offline cut relinked to the camera originals by source timecode. A piece's record.
- rasterio's windows and GDAL's geotransform: a window carrying its transform to the whole, windows
  of windows composed. A piece's record.
- Bazel's and Nix's hermeticity: a key holds all an action reads, and what is read and not held is
  how a cache goes stale. A series result below a period.
- ffmpeg's seeking, and H.264 and MPEG-TS: a seek that snaps to a keyframe under stream copy, a row
  decoded from the keyframe before it, a transport stream's timestamps that jump. A tool that cuts
  in time, over `00000.MTS`.

## A piece's record

Assumes: nothing.

Facts to weigh. `tools/region.py:origin` is the step in space. `plan.py:Entry.piece` is the name
of the nearest cutting node upstream, not an extent. `region.py:run` refuses a frame that is not
its file's plate.

- [ ] A piece's record is one value: the footage it is of, the pieces it was cut from, and its
  extent on the footage, a period of the footage's rows, a shape in the footage's pixels, or a
  shape a row over a period. Two records intersected are the record of the piece cut from both,
  and a row or a place lifted through one is the footage's. What a node's piece is, and a table's
  lift, are that value's, and no module computes its own.
  Check: a seam: a region within a period and a period within a region have one extent, and a
  place lifted through either is the footage's.
- [ ] The record holds a shape a row though no tool here makes one.
  Check: the same seam, a shape a row intersected with a period.

## A node's extent follows the wires

Assumes: A piece's record.

Facts to weigh. A walk is of one range, the window's or the clip's, and steps one chain
(`walk._Walk`, `chain_of`). A periods file reaches a `period` on a path input and not a wire, so
a document's range set from it reaches nodes no wire joins to the period, the series node whose
gate wrote the file among them: the detector's output setting the rows its own input is walked
over, by an edge no plan or key holds. `plan.plan` refuses a node whose inputs are of two pieces,
the plate among them; a served clip's pixels are H.264's and not the plate's, and a period's rows
are the footage's own.

- [ ] A node's extent is its inputs' intersection, cut where a cutting node cuts. A node no
  `period` feeds is walked over the rows it is walked over with none in the document.
  Check: a seam: a stepped node above a `period` and one below it, the one above's key and held
  rows the same with the period chosen, moved and gone.
- [ ] The stepped nodes of one extent are walked together over it, and those of another apart over
  theirs.
  Check: a one-off over the crossings clip: `count` above a period and `track` below it, the rows
  each was stepped over.
- [ ] A periods file says the document and node whose gate wrote it, and a `period` that reads a
  file written by a node below it is refused, saying both.
  Check: a seam.
- [x] Kendrick: a node reading two pieces is refused, as today. A read across pieces, and a
  `lift` to an ancestor's extent, wait on a document that needs one.

## Outside a piece is absent

Assumes: A node's extent follows the wires.

Facts to weigh. `graph.gated` hands a series node downstream a gated-out row as a zero signal or
an empty table, so a sum, a mean or a count below it counts a row no one measured as a measured
zero, and an empty table reads as a row where nothing was found. `walk._Walk.step` hands a
stepping tool `None` where nothing feeds it.

- [ ] A row outside a node's extent is absent to what reads it: no node is computed or stepped
  at it, and no table written holds a record of it.
  Check: a one-off over the crossings clip: a csv below a period, its rows against the period's.
- [ ] A gated-out row is handed to a stepping tool downstream as absent, apart from a zero and
  from an empty table, and what a tool's state does across it is the tool's, each stepping tool
  saying so. Changes keys: it is said before it lands, and the held files of the documents in use
  are walked again, as `docs/spec/what-a-node-declares.md`'s Keys that move once.
  Check: a one-off over the crossings clip: `count` below a band, its result over a gated-out run
  against the same rows read as zero.

## Rows below a cut are the footage's

Assumes: A piece's record.

Facts to weigh. A frame node's value is kept by key and row (`graph.Graph._compute`). A stepped
tool's `step` is handed its row's place in the walk's range and not in the footage
(`walk._Walk.step`). A region's served clip is of the whole video's rows.

- [ ] Every row a node below a period is handed, computes at, is held at and writes is the
  footage's.
  Check: a one-off over the crossings clip: a tracks csv below a period, its rows against the
  same node's above it.
- [ ] To what reads it by the row, a period's key is its input's: a node below a period that does
  not step has the key it has above, and computes no row held above.
  Check: a seam: such a node below a period and one beside it, of one tool and params, one key.
- [ ] A node below a period that does not step and reads a neighbouring row reads the footage's, inside the
  period or not.
  Check: the same seam, a node reading the row before at the period's first row.
- [ ] Below a region, a row is the footage's as it is above it.
  Check: a one-off: a node's rows below a served region against the plate's.

## A series result below a period

Assumes: Rows below a cut are the footage's; A node's extent follows the wires.

Facts to weigh. A stepped node's result at a row depends on where its walk began; series in this
section's name is any node that steps, a frame tool that keeps state among them. A held run
(`held.Run`) holds the row it began at, and `held.py:Runs.over` serves a range by cutting it from
the run that began earliest whatever that row. `window.py:PlayerWindow._ask_window` hands the
window what `Runs.part` holds of the stepped nodes and steps the rest from the window's first
row, so a node stepped there reads, from a node handed it, rows walked from an earlier row; the
run that walk makes is held under the same keys as a walk of the clip from row 0, with other
values at the same rows, and the window shows whichever was held first.

- [x] Kendrick: a stepped node's result below a `period` is the chosen period walked alone, its
  origin the period's first row. It is the caveman way, the period cut to a clip of its own and
  the pipeline run on it, and so the ground truth; a walk cut from a longer one agrees with it
  only for a tool whose reach is bounded and declared, by A tool's reach in rows.
- [ ] A result below a period is the result of the same document run on the period cut to a
  lossless clip of its own, row for row and equal.
  Check: a one-off under `docs/findings/experiments/`, the golden master: each period of a
  periods file over the crossings clip cut by frame index, not timestamp, to a lossless clip, the
  document run on it, and its tables against those below the period, the rows that differ said.
  A cut through H.264 adds the encoder's difference and isolates nothing.
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
- [ ] A held stepped result is addressed by its key, its origin and its rows, and a walk handed rows
  of one origin steps nothing of another from them. A run serves a range at the origin it is
  asked at, a period's first row or the window's, and one of another origin only as A tool's
  reach in rows allows.
  Check: a seam: `Runs.over` across a period walked from its own first row and the same rows cut
  from a longer run, two results under one key, each served at its own origin alone; and the
  window handed `track`'s rows of row 0 and stepping `count` from its own first row, refused.

## A tool's reach in rows

Assumes: A series result below a period.

Facts to weigh. `travel` and `transitions` step a state that is the row before and nothing
earlier; `track`'s ids are of every row since its walk began. No tool says how far back its result
at a row reads, so the player can serve a piece from no run of another origin, nor say how many
rows before a piece's first row a walk begins for its first rows to be a longer walk's. The
registry is the one reader of what a tool declares (`docs/spec/what-a-node-declares.md`).

- [ ] A stepping tool declares its reach in rows, how far before a row its result there reads, or
  none, its reach unbounded; one left unsaid is unbounded, as is one whose memory fades and never
  ends.
  Check: `tests/test_registry.py`.
- [ ] A node's reach is its own added to that of the stepped nodes it reads, unbounded where any
  is. A run of another origin serves a piece's rows where it began at least the node's reach
  before them, and a piece whose nodes' reach is bounded is walked from that many rows before its
  first row, its extent unmoved.
  Check: a seam: `travel` below a period served from a walk of the clip, and `track` not; and a
  one-off, each stepping tool's result over a period walked alone against the same rows cut from
  the clip's walk, the rows after the period's first at which they differ against its declared
  reach.

## The periods a `period` chooses among

Assumes: nothing.

Facts to weigh. What a person made reaches a tool as a file on a path input, whose loader's
answer lies in the node's key (`tools/resolve.py`'s `PATHS`). A series result's band is the rows
under its gate (`graph.gated`).

- [ ] A file of periods is written from a series result's gate: the footage it is of, and each
  period as the footage row it begins at and the row past its last, so periods that touch do
  not overlap and an empty one can be said.
  Check: a one-off over the crossings clip: the file's periods against the gate's rows.
- [ ] A `period` holds a file's periods and a choice of one, and a file of another footage is
  refused, saying both. Periods of a file that overlap are each a period, none merged with
  another.
  Check: a one-off.

## A tool that cuts in time

Assumes: A piece's record; A node's extent follows the wires; A series result below a period; The
periods a `period` chooses among.

Facts to weigh. The tree sets the rows a document is walked over for a served clip alone. Not
sized: how far a node that serves no file and sets the rows of its extent reaches into `plan.py`
and `walk.py`.

- [ ] What reads a `period` is walked over the chosen period's rows.
  Check: a one-off over the crossings clip: the rows a node below a period hands out.
- [ ] A period's rows are in no key. A period moved that is not the chosen one moves nothing below
  it; the chosen one moved moves the extent of every node below it and the
  origin of a stepped node below it.
  Check: a seam.
- [ ] A period under a region and a region under a period both run, and their pieces have one
  extent.
  Check: a one-off over the crossings clip.

## Not here

Walking every period, or every piece, with no window, and the tables it writes: the fourth of the
review's E2 (`docs/systems-review.md`), which has no spec yet; pieces that overlap fold back up by
the model's address there, both kept. A tool that makes a shape a row. Periods
handed to a `period` live by a series node above it, which is a frame node reading a series
result. Periods of two results intersected. A margin grown or cut around a piece, which changes
its extent; a pre-roll set by hand, the one a bounded reach needs being inferred by A tool's
reach in rows. Region's key, which holds its cut, a served clip's pixels being H.264's and not
the cut's. A read across pieces, and a lift. Identity across pieces.
