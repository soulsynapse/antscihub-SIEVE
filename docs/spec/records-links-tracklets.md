# Records, links, tracklets: what the detection and tracking tools promise each other

Read with the registry's type report (`python -m sieve_player.registry`), the live statement of what
feeds what, with `tools/_table.py`, which holds the table kind, and with docs/spec/identity.md, whose
identity pass reads what this records. Every tool and column word below is a placeholder:
docs/spec/tool-naming.md makes the words Kendrick's.

## Why

Kendrick: the rework "isn't for the tools per-se, it is for all the future tools so I don't have to
break stuff". There are to be several ways of tracking side by side, a fast one, an accurate one, one
that predicts, one that is told a count, and what is held to here is that a new one is a tool wired
in and no change to the tools around it. Three things he means to do later are the test, and none is
a deliverable: a costlier pipeline run over crops chosen from the track records, for a focal
individual; two individuals that merge counted as one, decided after the tracks are made; and two
detections whose results are joined, a tag matched to the animal under it.

What stands in the way today is that a fact a later tool needs is not recorded by the earlier one,
so each tool guesses it and the guesses are welded to each other. A contact between two animals is
detection's fact, and `track`'s `merge_ratio` and `resolve.contacts` each derive it again from
centroids and boxes. `blobs`' filled contour is not the region's own pixels wherever the region has a
hole or a concavity (docs/findings/2026-11-12-blobs-contour-against-mask.md on `v5-runs`); `detect`
has no footprint, and `sample`, `attach` and `filter` read its box without saying so. Every reader of
tracks reads the one column `id`, so a second way of grouping records has nowhere to go.

The runtime decides the shape. A tool has one output. A series tool reads its one input and nothing
else, and its `step` is causal and is told no absolute row. A frame tool reads any row of its inputs
and any second plane. So a frame tool puts evidence on records and a series tool only associates
records across rows; whatever needs a plane or a neighbouring row sits before the linker. The wire
types stay `blobs` and `tracks`, and the contracts are `tools/_table.py`'s.

## How to read this

As identity.md's: each `##` below that carries boxes is a deliverable, with an `Assumes:` line, a
sentence of why, and done-when assertions, each a box with a `Check:` that is a one-off unless it
holds a seam or an invariant, by the Tests section of CLAUDE.md. A box is ticked by a session once
its check passes in the tree; a session never unticks or rewrites an assertion. Nothing here says
how. No deliverable removes a tool: `blobs`, `detect` and `track` are held to the contracts and stay.

## The chain as it stands, measured

Assumes: nothing.

A tool held to a contract is read against itself before, on the same rows.

- [ ] A finding holds, for `blobs`, `detect` and `track` as they stand on the crossings clip, the
  purb document and a thermal-hysteresis crop, the records a row, the ids and their lengths, and
  the linker's own events as docs/findings/2026-11-01-track-diagnostics.md counts them.
  Check: a one-off under docs/findings/experiments.

## A record's name

Assumes: nothing.

`step` is told no absolute row, and a filter may sit between the tool that made a record and what
associates it, so neither the row nor a record's place in its table names it.

- [ ] Every record carries a `key`, its row and its index in the table it was made in, unique
  within a table and kept by every tool that keeps records.
  Check: a seam: a table through `filter`, `sample` and `attach` has the keys it had.
- [ ] A tool that makes records gives each a key of its own, so two nodes' keys are never compared;
  two tables are related by where their records lie, as `attach` relates them.
  Check: a one-off.
- [ ] A detector whose every input is static does not hand each row the first row's keys.
  Check: a one-off over a detector fed by a static mask.

## A record's footprint

Assumes: nothing.

A record made from a mask has pixels, one made from geometry has an outline, and one made by a
detector of boxes has neither; a reader is told which, and never given the box unasked.

- [ ] A table says what footprint its records have: runs, a polygon, or none.
  Check: a seam: `blobs`' table says runs, `region.table`'s a polygon, `detect`'s none.
- [ ] `blobs`' records carry their region as runs where they carried a contour, and a footprint
  is the region's own pixels, holes kept.
  Check: a seam: a shape with a hole, its footprint against the mask it was found in.
- [ ] A reader asking for a footprint of a record that has none raises, naming what it lacks,
  unless it asked for the box.
  Check: a seam, in the same test.

## Links

Assumes: A record's name.

Which records of the next row a record becomes is a fact of the footage, and a contact is where
the answer is not one. Whatever finds it, by pixels, by flow, by a model, writes it in one place.

- [ ] A table may carry links: for each record the keys of the records of the row before and of
  the row after that it continues, and how many of each. Any tool may write them, one writer to a
  table, and a tool that reads them reads no other sign of a contact.
  Check: a seam: a table with links through `filter` keeps them, and a link to a record `filter`
  dropped reads as none.
- [ ] One frame tool writes them from the overlap of footprints in the row before and the row
  after; the same whichever row was asked for first, none before the first row and none after the
  last.
  Check: a seam: two regions that merge and part, the links at each row, asked forwards and
  backwards.

## What groups records

Assumes: nothing.

A tracklet, an individual, a pair counted as one and an identity are each a way of grouping the
same records, and a reader that knows one column's name can be handed only one of them.

- [ ] A tracks table has one or more grouping columns, `id` the first; a tool that makes another
  adds a column and leaves those it read.
  Check: `tests/test_columns.py`, a grouping column added below `track` and read beside `id`.
- [ ] `kinematics`, `transitions`, `travel`, `tracks-filter`, `csv` and the draw read the grouping
  column they are told, `id` where they are told none; they hold a group's key as an integer of
  any width.
  Check: their tests as they stand, and one of them over a second column; `resolve.tables_of`
  reads an id past int32.
- [ ] One reading of a tracks series gives, for a grouping column, each group's rows and first and
  last records, and from the links where the table has them its parents and children, an edge
  being a link whose two ends differ in group; `tracks-filter`, `kinematics` and `resolve` read
  that and loop over no record of their own.
  Check: their tests as they stand.
- [ ] `resolve` reads a contact from the edges where the table has links, and as it does now where
  it has none.
  Check: `tests/test_resolve.py` as it stands, and its merge and parting over a table with links.

## A linker that reads the links

Assumes: Links, What groups records.

The contracts are shown to hold by one tool that uses each; it stands beside `track` and replaces
nothing.

- [ ] A series tool gives a record its predecessor's `id` where it has one predecessor and that
  predecessor one successor, and otherwise an id that is the record's own key. `step` holds to
  `run`.
  Check: `tests/stepping.py`'s `hold`, and a seam: a merge and a parting make five ids, none
  across the contact, and a gated-out row ends every id.
- [ ] A walk begun at any row gives every tracklet born inside it the id a walk of the clip gives.
  Check: a seam: the linker stepped from two first rows.
- [ ] Its tables carry no footprint and are flat.
  Check: `held.py`'s `_flat` takes its series whole.

## Under a piece

Assumes: A record's name, Links; docs/spec/pieces-of-footage.md's A piece's record and its A table
written is in the footage's own pixels and rows.

Facts to weigh. A key, a link and a group's key may each hold a row, the first columns of a table
that do, and `sieve_player/wire.py`'s units are all of a plane's pixels: pieces-of-footage.md
writes a column that says none as it is. A key is unique within a table and an id within a walk,
so two regions' tracklets of one video hold the same ids. A tool reading the row before and after
meets a stretch's edge below a `period`. A table's dtype carries the size of the plane it was found
in and not where that plane lies, so `attach` and `sample` between a table found in a region and a
plane of the plate scale and do not move, and `plan.py` refuses a node that reads across a cut.
A record cut by a region's edge has the footprint and the area of the part inside.

- [ ] The row a key, a link and a group's key hold is the footage's wherever a csv writes it.
  Check: a one-off: a tracks csv written below a cut in time, its ids' rows against its `row`
  column.
- [ ] A link at a piece's first row reads none before and at its last none after, whatever rows
  the footage has outside the piece.
  Check: the Links seam, below a cut in time.
- [ ] A csv's key line naming the piece is what tells two pieces' equal ids apart.
  Check: pieces-of-footage.md's one-off of two regions, the two files' ids.

## What the three ask

Each is walked through what is above. What holds is a contract here; what stands in the way is
said with where it lives, and none of it is built by this spec.

| | What it reads of this spec | What stands in the way, and whose it is |
|---|---|---|
| A costlier pipeline over crops chosen from tracks | `tracks-filter` picks the groups; a group's rows and boxes are one reading | A piece's record holds a rectangle and a range of rows, and a crop that follows an animal is a rectangle a row: pieces-of-footage.md's. What the crop's chain finds is joined to the tracks by where it lies, which wants a table to say where its plane lies and `plan.py` to let a node read across a cut: pieces-of-footage.md's and the runtime's |
| Two that merge counted as one, later | a tool over the edges adds a grouping column; every reader is told which column | a contact of many to many, if links keep only the largest overlap: Open, below |
| Two detections joined, a tag to its animal | by the row, `attach` lays one table's columns on the other's records before any linker, and identity.md's `resolve` reads them | joined as tracks, nothing: `plan.py` walks one frame node, so a second detection's linker does not run, and a series tool reads one input. The runtime's |

## What each coming tool asks

| Tool | Where it sits | What it strains |
|---|---|---|
| A tag detector | a record with a polygon, a code and a heading | nothing |
| A learned detector of boxes | a record with no footprint | nothing |
| Keypoints, an embedding | columns of a record | `with_column` keeps no sub-array shape; an object column, or that mended |
| A split of touching animals | a frame tool, records and a plane in, keys its own | it cannot read its own row before |
| An animal count | a frame tool by the row, or tracks to tracks by the run | nothing |
| A link by flow | a second frame tool writing the links | nothing |
| A linker that predicts and assigns, a linker told a count | series tools writing `id`, as `track` is | nothing: an edge is a link across two groups |
| A stitch over dropped records | tracks to tracks, a grouping column of its own or `id` rewritten | nothing |
| Individuals over tracklets, pairs as one | tracks to tracks, a grouping column | many-to-many edges, as above |
| Corrections from a file | identity's | see Open |
| A score against a reference | tracks and a path in, matched by position | a one-off first |
| Posture, patches | frame tools before the linker | patches are an object column |
| Records interpolated over a gap | tracks to tracks | a record said not to be observed |
| An animal followed across pieces | not here, as pieces-of-footage.md's Not here | an id names no piece |

## Non-goals

- Any tool in the two tables above, and any of the three.
- Removing or renaming `blobs`, `detect` or `track`, or a param of one; a saved document loads as
  it did.
- Saying which way of tracking is right. identity.md's refusal of a linker tuned without ground
  truth is about `track`'s knobs and is untouched; a second linker is a second tool.
- A change to `sieve_player`, beyond what A record's name's third box and Under a piece's first
  may ask.

## Open

- Every tool and column word here.
- Whether links keep every overlapping neighbour, an object column and a table that is not flat,
  or the largest before and after with counts, flat, a contact of many to many then keeping its
  counts and losing an edge. The second is cheaper to hold; the first is what counting a merged
  group as one reads.
- Whether a key is one column holding a row and an index, or the two apart; whether a row is a
  unit in `sieve_player/wire.py`; or whether what is below a `period` is handed the footage's row
  numbers, so a key is the footage's as it is minted and nothing lifts it.
- Whether `blobs` keeps `contour` beside runs for a document that draws by it.
- Whether a labels row names a row and a point, read against the footprint there, where it now
  names a track id that every upstream knob moves.
- The least overlap that links two records.
- What `mean`, `peak`, `core` and `split` are to `blobs`; identity.md's Open asks it already and
  this neither answers nor needs it.
