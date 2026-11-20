# A cut in time, and the record every cut keeps

Read with `VISION.md`, whose picture this holds the tree to; with `tools/region.py`, the cut in
space; with `sieve_player/plan.py`, `sieve_player/walk.py` and `sieve_player/held.py`, which
plan, walk and hold what a cut reads; and with `docs/spec/what-a-node-declares.md`, whose keys
this assumes.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

## Why

A pipeline picks the stretches of the footage worth a closer look, and a heavier one runs inside
one of them, as a heavier one runs inside a region. Whatever is found there is the footage's: its
rows and pixels are the footage's, and it lays back over the footage beside what was found
around it.

## The model

A piece is a subset of one footage's pixels and rows, with a reference to the piece it was cut
from. A region is a shape over every row, a period every pixel over a stretch of rows, a region in
a period both, and a track a shape a row over a stretch. A piece of a piece is the intersection of
the two. A cut restricts and never renumbers: a row and a place below a cut are the footage's.

What a value at a row reads sets whether it is the same below a cut. A value read from rows a
bounded distance away is the same whichever piece it is computed in, once those rows are read,
the footage's rows outside the piece among them. A value that depends on where its walk began is
of the piece walked, and the same rows cut from a longer walk are another result that may equal
it.

## Referents

What each settled, and the box it bears on. A session building a box reads its referent first.

- Nuke's NDK, `_validate`, `_request` and `engine`: an op's output box apart from the box asked of
  it, the ask passed upstream and grown by each op that reads past it, the hash not holding the
  ask. Rows below a cut are the footage's; A tool that cuts in time's keys.
- OpenFX's `getRegionOfDefinition`, `getRegionsOfInterest` and `getFramesNeeded`: the same split as
  a standard, and the last the rows an output row reads. A frame node reading a neighbouring row.
- Halide (Ragan-Kelley and others, PLDI 2013): each stage's needed input inferred from the output
  asked of it, never set by hand. The Open line on a tool's reach.
- The Dataflow Model (Akidau and others, VLDB 2015): event time apart from processing time, and
  the session window, a stretch bounded by gaps. Rows below a cut are the footage's; The stretches
  a period chooses among.
- Fading memory (Boyd and Chua, 1985): when a stateful operator forgets where it began, so a walk
  begun earlier converges on one walked alone. A series result below a period.
- BED, GFF and bedtools: intervals half-open from 0 against closed from 1, the off-by-one between
  them, and intersect, merge and complement over stretches. The stretches a period chooses among.
- rasterio's windows and GDAL's geotransform: a window carrying its transform to the whole, windows
  of windows composed. A piece's record.
- Bazel's and Nix's hermeticity: a key holds all an action reads, and what is read and not held is
  how a cache goes stale. A period's key being its input's.
- ffmpeg's seeking, and H.264 and MPEG-TS: a seek that snaps to a keyframe under stream copy, a row
  decoded from the keyframe before it, a transport stream's timestamps that jump. A tool that cuts
  in time, over `00000.MTS`.

## A piece's record

Assumes: nothing.

Facts to weigh. `tools/region.py:origin` is the step in space. `plan.py:Entry.piece` says which
cutting node a node's inputs are of. `region.py:run` refuses a frame that is not its file's plate.

- [ ] A piece carries the footage it is of, the piece it was cut from, and its extent on the
  footage: a stretch of the footage's rows, a shape in the footage's pixels, or a shape a row over
  a stretch. A piece cut from a piece has the intersection of the two extents.
  Check: a seam: a region within a stretch and a stretch within a region have one extent.
- [ ] The record holds a shape a row though no tool here makes one.
  Check: the same seam, a shape a row intersected with a stretch.

## Rows below a cut are the footage's

Assumes: A piece's record.

Facts to weigh. A frame node's value is kept by key and row (`graph.Graph._compute`). A stepped
tool's `step` is handed its row's place in the walk's range and not in the footage
(`walk._Walk.step`). A region's served clip is of the whole video's rows.

- [ ] Every row a node below a period is handed, computes at, is held at and writes is the
  footage's.
  Check: a one-off over the crossings clip: a tracks csv below a period, its rows against the
  same node's above it.
- [ ] To what reads it by the row, a period's key is its input's: a frame node below a period has
  the key it has above, and computes no row held above.
  Check: a seam: a frame node below a period and one beside it, of one tool and params, one key.
- [ ] A frame node below a period that reads a neighbouring row reads the footage's, inside the
  stretch or not.
  Check: the same seam, a node reading the row before at the stretch's first row.
- [ ] Below a region, a row is the footage's as it is above it.
  Check: a one-off: a node's rows below a served region against the plate's.

## A series result below a period

Assumes: Rows below a cut are the footage's.

Facts to weigh. A stepped node's result at a row depends on where its walk began.
`held.py:Runs.over` serves a range by cutting it from the run that began earliest, and the
player's window is served by it too, so whichever rule a period is held to, the window is held to
it unless it is said to be no piece.

- [ ] Kendrick: a series node's result below a period is the stretch walked alone, or the same rows
  cut from a walk of what the stretch was cut from; this line says which. Recommended: walked
  alone, the second being right only for a tool whose reach in rows is bounded and declared, which
  no tool declares.
- [ ] Kendrick: the player's window is a view of the clip's rows that any held run serves, or a
  piece held to the answer above; this line says which. Recommended: a view.
- [ ] A series node's held rows serve a stretch only where they are what the first answer says the
  stretch's result is, and the window's as the second says.
  Check: a seam: `Runs.over` across a stretch held from its own first row and the same rows cut
  from a longer run.

Open: whether a series tool may declare its reach in rows, so that a longer run serves a stretch.
Recommended: not here, the reach being what `docs/systems-review.md`'s E1 declares of a tool.

## The stretches a period chooses among

Assumes: nothing.

Facts to weigh. What a person made reaches a tool as a file on a path input, whose loader's
answer lies in the node's key (`tools/resolve.py`'s `PATHS`). A series result's band is the rows
under its gate (`graph.gated`).

- [ ] A file of stretches is written from a series result's gate: the footage it is of, and each
  stretch as the footage row it begins at and the row past its last, so stretches that touch do
  not overlap and an empty one can be said.
  Check: a one-off over the crossings clip: the file's stretches against the gate's rows.
- [ ] A `period` holds a file's stretches and a choice of one, and a file of another footage is
  refused, saying both.
  Check: a one-off.

## A tool that cuts in time

Assumes: A piece's record; A series result below a period; The stretches a period chooses among.

Facts to weigh. The tree sets the rows a document is walked over for a served clip alone. Not
sized: how far a node that serves no file and sets those rows reaches into `plan.py` and
`walk.py`.

- [ ] What reads a `period` is walked over the chosen stretch's rows.
  Check: a one-off over the crossings clip: the rows a node below a period hands out.
- [ ] A stretch moved that is not the chosen one moves no key. The chosen one moved moves the key
  of a series node below the period under the first answer and of none under the second, and of no
  frame node under either.
  Check: a seam.
- [ ] A period under a region and a region under a period both run, and their pieces have one
  extent.
  Check: a one-off over the crossings clip.

## What leaves the player is in the footage's rows and pixels

Assumes: A piece's record.

Facts to weigh. A csv written below a region is in the cut clip's pixels, so two regions' tables
cannot be laid side by side or drawn over the footage. `rescale` and `coarsegrain` hand out a plane
of another size than the piece's, and a table's dtype carries the plane it was found in
(`tools/_table.py:plane`). `attach`'s area is in the mark's plane. A column's unit is said where it
is minted and carried on the dtype; one the dtype says nothing of may have lost its unit
(`docs/findings/2026-11-17-what-keeps-a-dtypes-metadata.md`). `csv.py:default_name` is the
footage's stem and the rows, so two regions of one video that serve no clip name one file.

Open: whether a table's positions are moved to the footage's pixels where it is written, or are
minted in them. Recommended, and a session may build on it: where it is written, the table
carrying its piece and plane.

- [ ] A csv's rows are the footage's, and each column that says a unit is in the footage's pixels,
  scaled along its axis by its plane against the piece's size and, a position, moved by the record;
  a column that says none is written as it is. Its name and key line say the piece, the plate where
  there is no cut.
  Check: a one-off: a csv below a region and one below a region and a `rescale`, positions read
  back against the plate; one below an `attach`, its mark's area against the mark's plane; two
  regions of one video, two files.
- [ ] A table with a numeric column its dtype says nothing of is not written: the write raises,
  naming the column.
  Check: `tests/test_csv.py`, a seam.

## Not here

Walking every stretch, or every piece, with no window, and the tables it writes. A tool that makes a
shape a row. Stretches handed to a period live by a series node above it, which is a frame node
reading a series result. Stretches of two results intersected. A margin grown or cut around a
piece. Region's key, which holds its cut, a served clip's pixels being H.264's and not the cut's.
Identity across pieces.
