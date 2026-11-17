# A pipeline run over pieces of footage

Read with `docs/systems-review.md`, E2; with `docs/spec/what-a-node-declares.md`, parts of which
this assumes; with `tools/region.py`, the cut in space; with `tools/csv.py`, which writes a table;
and with `sieve_player/bare.py`, the walk with no window.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

## Why

The tuned document draws a region on the plate, runs its chain inside that one region and writes
one csv. The plate holds several regions, the experiment several videos, and within a video only
some stretches matter. Every further table is a region chosen by hand, a clip walked and a csv
written. Kendrick: it "is going to have to exist" and is "definitely what it is reaching for right
now".

Houdini's TOPs is the one followed. A piece is a work item that carries how it was cut, passed
down to the items made of it; a node makes an item for each choice of each item above it; each
item is a job of its own; and a partition waits for all and holds what each carried. Left out, as
E2 has it: the farm, items made while the work runs, attributes as a general store, and a second
network.

## A piece's record

Assumes: nothing.

Facts to weigh. `tools/region.py:origin` is the step in space. `plan.py:Entry.piece` says which
cutting node a node's inputs are of.

- [ ] A piece carries the steps that cut it, each a range of rows or a rectangle relative to the
  piece above, and their sum on the footage.
  Check: a seam: a rectangle within a range within a rectangle sums to the footage's own pixels
  and rows.

## A table written is in the footage's own pixels and rows

Assumes: A piece's record; `docs/spec/what-a-node-declares.md`'s What a wire carries is in one
table. Changes what a csv below a region holds.

Facts to weigh. A csv written below a region is in the cut clip's pixels, so two regions' tables
cannot be laid side by side or drawn over the footage. A piece's record holds cuts and no scale:
`rescale` and `coarsegrain` hand out a plane of another size than the piece's, and a table's
dtype carries the plane it was found in, `tools/_table.py:plane`. Which columns of a table are in
that plane's pixels is the wire table's to say.

- [ ] A csv's rows are the footage's by its piece's record, and each column the wire table has as
  in the plane's pixels is in the footage's, scaled by the table's plane against the piece's size
  and, a position, moved by the record; whoever writes it. Its key line says the piece.
  Check: a one-off: a csv written below a region, and one below a region and a `rescale`, their
  positions read back against the plate.

Worth a look: a csv of the purb document before and after, since what reads one downstream reads
other numbers.

## A document walked with no window, under a named choice

Assumes: A table written is in the footage's own pixels and rows;
`docs/spec/what-a-node-declares.md`'s The registry is the one reader of what a tool declares.

Facts to weigh. `bare.py` walks the clip under the choice the document holds, started by the
window, and drives its walk itself with no worker. Part 4's H6: its decoder is told where the
store is by a global the window alone sets. What a `csv` node writes is `csv.py`'s `write` under
its `default_name`, called by `tools/_csvfile.py:widget` and no facet; what a region offers is
`region.py:crops`, no facet either.

Open: whether the command is `bare.py` handed a choice or a second walker beside it.
Recommended, and a session may build on it: one, which the window starts as it starts `bare.py`.

- [ ] A command walks a document under a choice named for each cutting node, with no window, and
  writes what its `csv` nodes write.
  Check: a one-off: its csv equals the one the player writes of the same document and choice.
- [ ] What the command calls of a tool, to write and to learn what a cutting node offers, is a
  facet the registry's table lists.
  Check: the seam of the registry as the one reader, which stands.
- [ ] The command's decoder keeps and reads a file's frame times in the store as the player's
  does.
  Check: the same one-off over a transport stream, `00000.MTS`.

## Every piece

Assumes: A document walked with no window, under a named choice.

Facts to weigh. A geometry file is a video's, so what a region offers is known under a video and
not before it. A process a piece decodes the plate once a piece wherever its region serves no
clip.

Open: how many pieces are walked at once. Recommended, and a session may build on it: a count the
command is given, one where none is.

- [ ] One command runs that one for every choice: for each video its selector matches, the
  product of what each cutting node offers under that video; each a process, and it ends when all
  have.
  Check: a one-off over the purb document: a csv a piece, each equal to the one made by hand.
- [ ] A piece that fails is said with its choice, and the others finish.
  Check: the same one-off with one piece's geometry made to refuse.

## A bout walked alone

Assumes: nothing.

A stepped node's result at a row depends on where its walk began, so a tracker's identities in a
bout walked alone are not those of the same rows cut from a walk of the whole clip.
`held.py:Runs.over` answers today by cutting a range from the run that began earliest. TOPs and
Bonsai both answer alone.

- [ ] Kendrick: a piece's result is the piece walked alone, or the same rows cut from a walk of
  what it was cut from; this line says which.

## A held run serves what a piece's result is

Assumes: A bout walked alone.

- [ ] A stepped node's held rows are served for a range only where they are what the answer above
  says that range's result is.
  Check: a seam: `Runs.over` across a range held from its own first row and the same range cut
  from a longer run.

## A tool that cuts in time

Assumes: A piece's record; A held run serves what a piece's result is;
`docs/spec/what-a-node-declares.md`'s A param is declared once.

Facts to weigh. A `region` holds the shapes and a choice of one, and narrows the footage to it.
The tree sets the rows a document is walked over for a served clip alone. Not sized: how far a
node that is no served file setting those rows reaches into `plan.py` and `walk.py`.

- [ ] `period` holds a table of stretches and a choice of one, and what reads it reads the rows of
  that stretch, as what reads a region reads its rectangle.
  Check: a one-off over the crossings clip: the rows a node below a period hands out.
- [ ] Where a piece's result is the piece walked alone, a period's key is of the stretch chosen;
  where it is the same rows cut from a walk of what it was cut from, the keys below a period are
  that walk's and no stretch is in one.
  Check: a seam: the keys below a period stand across a stretch moved that is not the chosen one;
  across the chosen one moved they move under the first answer and stand under the second.
- [ ] A period under a region and a region under a period both run, alone and under Every piece.
  Check: a one-off over the crossings clip.

## Not here

A farm. Pieces made while a walk runs. Tables of several pieces merged into one. Identity across
pieces.
