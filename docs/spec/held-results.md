# Held results: what a walk computed for a series node is kept, over the clip, across the window's moves and across sessions, and what is kept is shown

Written 2026-11-12 from the conversation that read `docs/findings/2026-11-12-what-a-walk-holds.md`, on
v5-monitor and outside its scope; the branch this is built on is not yet cut. Read with that finding,
which is the measurement this is argued from; with `sieve_player/worker.py`, whose `_Walk` holds a range's
stack and stepped results and whose `STACK_BYTES` closes it; with `sieve_player/graph.py`, whose `nbytes`
is the count and whose `gated` is what a result becomes on its way out; with `sieve_player/plan.py`, whose
keys say what a result is a result of; with `sieve_player/window.py`, whose `results` and `clip_results`
are the two things the player keeps of a walk; and with `docs/spec/bake.md`, the one way a result reaches
a disk today.

## Why

A clip walk steps every node of the series chain over every row and holds the lot until it ends. On the
purb document the finding has an hour of that at about the cap, nearly all of it two nodes' tables, and a
signal at under a megabyte. Of what is held, two things are read: the pinned traces, and a series bake of
the one node it sits on. The rest goes, and it goes easily. The window and the clip are two ranges that
share nothing, so a window moved onto rows the clip walk already has is stepped again; a window moved ten
rows drops its whole result, overlap included; a frame tool's change drops the clip's rows; and closing
the video drops everything. A user moving the playhead about loses what a full walk would give back
unchanged.

Kendrick's word of 2026-11-12 is that this is the wrong default: a signal is free to hold for virtually
any clip, so it is kept through basically anything, here and into the next session; a table is not free,
so it is kept as far as the memory allows, released when it does not, and the user is shown which. The
line every program of this kind draws is between a cache, automatic, in memory and let go without a word,
and a bake, asked for, on disk and kept until freed: Blender's physics cache beside its Bake, Houdini's
Cache SOP beside its File Cache, a node's cache flag beside Nuke's DiskCache. This is the cache. The store
stays what `docs/spec/bake.md` made it, the place for what is large and asked for; what is small lives
beside the document.

What bounds it. A result is only reusable where it is the same result, and for half the series tools the
value at a row depends on where the walk that made it began; that is the first deliverable's to say and
the one place this could do harm quietly. And a thing kept is a thing that can be stale: a key that does
not see what changed serves a wrong row with nothing red.

## How to read this

As `docs/spec/monitor.md`'s How to read this, whole: deliverables with `Assumes:`, facts read off the
tree, boxes with a `Check:` that is a one-off unless it holds a seam or an invariant, `Open:` lines that
are Kendrick's to settle, `Fork:` lines taken by observation and never unobserved, and nothing that says
how.

Words. A result is *held* when it outlives the walk's turn that made it. A node's result is *free of its
range* when its value at a row is the same whatever range was walked, and *bound to its range* otherwise.
The *cap* is the bytes held results may take together. A table is *released* when its bytes are let go
and the row is as one never walked.

## Which results are the same result

Assumes: nothing.

Everything after this leans on serving a row from a result some other walk made, which is only sound
where the two walks agree at that row.

Facts to weigh, read 2026-11-12. A stepped node's state is None at its walk's first row. `track` numbers
its ids from there and holds a track back until it has `min_rows`; `travel` and `transitions` read 0 at
it; `kinematics` carries rows across a gap. So a window walk's tracks at a row and the clip walk's at the
same row are two answers, and every node downstream of `track`, `count` over tracks among them, inherits
that. `reduce` over a frame node, and `count`, `size` and `spacing` over blobs, have no state and read a
row alone. `smooth`, `tracks-filter` and `resolve` have no `step` and are a property of the whole range
they are run over, so theirs is the same result only over the same rows. A result carries its node's key
and its start beside it and the key does not hold the range. A key is the node's tool, its params and the
keys upstream (`plan.key_of`); it holds no band, and a node downstream is fed what the band upstream
keeps (`graph.gated`, `fed_row`); what a band's change does to a stepped node below it was not read. The
video's key is its path and the decoder's output (`plan.base_key`) and nothing of the file's bytes or
date. The registry reports whether a tool offers `step` and nothing about its state.

Open: what a row of a bound result is served from. Recommended, and what a session may build on: a bound
result is held as the run its walk made, from that walk's first row, and is never stitched to another
walk's; a row is served from the run that began earliest and reaches it, the clip walk's from row 0 where
there is one, since the answer with more rows behind it is the one a bake would write. The cost is that
the window's tracks change as the clip walk passes under it, ids among them.

Fork: how far a window walk's result is from the clip walk's at the same rows. Observed on the crossings
clip and its document, `track` and what reads it, as a finding: the rows from the window's first at which
the two differ, and by what. Where they agree past some few rows, the recommendation above stands and the
finding says how many; where they differ throughout, a window's bound results are its own and only a run
from the same first row serves it.

- [ ] Each series tool's result is said to be free of its range or bound to it, by something a session
  reads and the registry reports, and a tool that says nothing is taken as bound.
  Check: a registry test reads it off each series tool in `tools/`.
- [ ] A tool said to be free is free: stepped from two different first rows it gives the same share at
  the rows both reach.
  Check: `tests/stepping.py` holds it, beside what it holds of `step` against `run`.
- [ ] A held result is identified by everything it depends on: a band upstream that feeds it, and the
  footage as it was, are in what it is held under or it is not served across their change.
  Check: a one-off changes a band upstream and replaces the footage at its path, and reads no row served
  from before either.

## The count is what is held

Assumes: nothing.

The cap is only a fact about memory if the count is.

Facts to weigh, from the finding. `graph.nbytes` charges 64 for anything that is neither None nor an
array, and a signal's share is a numpy scalar, so a walk is charged sixteen times what its signals hold.
A table's contours are charged under every node whose rows carry them; whether `track`'s are the arrays
`blobs` made, held once and charged twice, was not read. `STACK_BYTES` is a constant with no stated
reason for its value, and the machine's memory is sampled by `sieve_player/machine.py`.

Fork: whether a contour is held once under two nodes. Observed by identity over a walk's stack and
`track`'s rows. Where it is, the count charges an array once however many rows carry it.

Open: what the cap is. Recommended: a share of the machine's memory, one named constant, read as the walk
begins; the cost is that a walk fits on one machine and not another under one document.

- [ ] What a walk is charged for a signal is what the signal's array holds.
  Check: a one-off walks a chain of signals and reads the walk's bytes against the arrays'.
- [ ] The bytes charged over a clip walk of the purb document are within a stated margin of what the
  process's memory grew by.
  Check: a one-off, on a machine left alone, the figures in a finding beside the 2026-11-12 one.

## A signal outlives its walk

Assumes: Which results are the same result; The count is what is held.

Facts to weigh. `_Walk.begin` drops every row held, and is what a moved window and a restarted clip both
call. `Worker.invalidate` restarts both ranges on a frame tool's change and `window._invalidate` empties
`clip_results`; the rows were under keys the plan no longer has, and nothing keeps a result under a key
that might come back. `rerun_series` reruns the chain over what is held. A stopped clip walk's rows stand
and its states are held with them, and asking for it again begins from row 0. The strip draws a shown
node's signal from the clip's result where there is one, else the window's (`window._show_pinned`), and
the plot draws the window's.

- [ ] A signal free of its range is held by its key over the clip's rows, with which rows it has, and a
  walk of either range that reaches a row held under the node's key steps nothing for it.
  Check: a one-off walks the clip, moves the window onto it, and reads no step of that node in the
  window's lane.
- [ ] A moved window keeps what it has of the rows it still covers, for a free result, and for a bound
  one by the first deliverable's Open.
  Check: a one-off moves a window by a tenth of its length and reads steps for the new rows alone.
- [ ] A signal held under a key the plan has left is kept while the cap allows and served when the key
  returns, a knob turned and turned back costing nothing.
  Check: a one-off changes a frame tool's knob and restores it, and reads the trace whole with no row
  walked.
- [ ] A clip walk stopped and asked for again goes on from the row it reached.
  Check: a one-off stops one midway, asks again, and reads each row stepped once.
- [ ] The trace, the strip and a tool's draw at the playhead read one held result for a node at a row,
  whichever walk made it.
  Check: a one-off reads the three at a row both ranges walked.

## Tables are kept until the cap

Assumes: A signal outlives its walk.

Facts to weigh. A walk past `STACK_BYTES` is refused: it closes at the rows it has and a bake of it is
abandoned (`_Walk.refuse`). A stepping tool needs its own state to go on and none of the rows behind it.
A node run whole needs every row of its source at each emit; a series bake is written from the finished
result all at once (`_Bake.from_clip`); a series node whose knob changes is stepped again from the rows
held upstream; a tool's draw reads the row's table; and csv's Write reads the window's rows. Each of those
is a reader of a table that a release takes away. The finding has what a node run whole costs over an
hour at every emit against once at its end.

Open: which tables are released first. Recommended: rows of the clip outside the window, farthest from it
first, under keys the plan has left before any it has; the window's own rows last, and a window that
alone passes the cap closes short as it does now.

- [ ] Past the cap a walk goes on: tables are released, the signals and the stepping tools' states are
  kept, and the walk reaches its last row.
  Check: a one-off walks a clip under a cap set low and reads every row's signal and the tables released.
- [ ] A released row asked for again, by a draw at the playhead, a window placed on it or a knob below
  it, is walked again as a row never walked is, and nothing reads an absent table as an empty one.
  Check: the same one-off draws at a released row and reads the row's own records.
- [ ] A reader that needs every row, a node run whole, a series bake, csv's Write, says what it lacks
  where rows are released, in the node's standing, and writes or shows no partial result as a whole one.
  Check: the same one-off, with a node run whole on the chain and a series bake asked.

## What is held is shown

Assumes: Tables are kept until the cap.

Facts to weigh. A walk's progress carries its bytes and the cap to the stream (`Graph.progress`), the
monitor lists a lane's stack among its stores, and the player shows neither. The strip's x axis is the
clip and it draws the shown nodes' signals; it draws nothing of which rows are held. By
`sieve-trace-no-derived-statistic`'s rule, Kendrick's and in no file here, a rendering neither hides a
value nor adds one.

- [ ] The strip shows, for the clip, which rows have a held result and which of those have their tables,
  so a row that costs nothing to visit is told from one that will be walked.
  Check: a one-off walks part of a clip under a low cap and reads the three states off the strip.
- [ ] The player says what is held in bytes against the cap, by signals and by tables, and says when a
  release has begun.
  Check: the same one-off reads the figures against the walk's own.

Worth a look: the strip on the purb document with the clip half walked and the window moved about.

## A second session starts with what the last one held

Assumes: A signal outlives its walk.

Facts to weigh. A document is a json file and knows its path once saved (`document.save`); one never
saved has none. A geometry file already sits beside the footage it describes. A store's bake is found
through the `baked` record on a bake node and through nothing else, so a node that is no bake node is
never served from a disk. A signal over an hour of the purb footage is under a megabyte and a table node
some hundreds, by the finding.

Open: when the file is written. Recommended: when the document is saved and when the video closes, once
each and whole, so a walk writes nothing as it runs; the cost is that a crash loses what was held since.

Open: how far tables go into it. Recommended: signals always; tables where the file stays under a stated
size, the player saying which it left out; the cost of the tables is a file that is no longer small.

- [ ] A saved document has one file beside it holding its held signals, each under what identifies it by
  the first deliverable, with the rows it has; opening the document serves them with no row walked.
  Check: a one-off walks, saves, opens the document in a fresh process and reads the trace and no step.
- [ ] A held result in the file that the document's plan no longer identifies is not served, and the file
  being absent, unreadable or of another document's is the same as there being none.
  Check: the same one-off, with a knob changed in the json, the footage replaced, and the file truncated.
- [ ] The file's size is stated where the player says what is held.
  Check: the same one-off reads it against the file's.

## Not here

Decided 2026-11-12 as outside this: a control that writes the cache to a bake, Blender's Current Cache to
Bake, held off on Kendrick's word; whether bake is a tool, a node of the player's as the video node is, or
a node at all, which he set aside for another time, this spec changing nothing of it and a bake on a
signal wire having less to do once this is built; a node run whole running once at a walk's end instead
of at every emit; and a table written to a disk as the walk makes it.
