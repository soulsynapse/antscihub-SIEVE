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

Assumes: A piece's record. Changes what a csv below a region holds.

Facts to weigh. A csv written below a region is in the cut clip's pixels, so two regions' tables
cannot be laid side by side or drawn over the footage.

- [ ] A csv's positions and rows are the footage's, by its piece's record, whoever writes it, and
  its key line says the piece.
  Check: a one-off: a csv written below a region, its positions read back against the plate.

Worth a look: a csv of the purb document before and after, since what reads one downstream reads
other numbers.

## A document walked with no window, under a named choice

Assumes: A table written is in the footage's own pixels and rows.

Facts to weigh. `bare.py` walks the clip under the choice the document holds, started by the
window, and drives its walk itself with no worker. Part 4's H6: its decoder is told where the
store is by a global the window alone sets.

- [ ] A command walks a document under a choice named for each cutting node, with no window, and
  writes what its `csv` nodes write.
  Check: a one-off: its csv equals the one the player writes of the same document and choice.

## Every piece

Assumes: A document walked with no window, under a named choice.

Open: how many pieces are walked at once. Recommended, and a session may build on it: a count the
command is given, one where none is.

- [ ] One command runs that one for every choice, the product of what each cutting node offers and
  of the videos its selector matches, each a process, and ends when all have.
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
  that stretch, as what reads a region reads its rectangle. Its key is of the stretch chosen.
  Check: a seam: the keys below a period across a stretch moved that is not the chosen one, and
  across the chosen one moved.
- [ ] A period under a region and a region under a period both run, alone and under Every piece.
  Check: a one-off over the crossings clip.

## Not here

A farm. Pieces made while a walk runs. Tables of several pieces merged into one. Identity across
pieces.
