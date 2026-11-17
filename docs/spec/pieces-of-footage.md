# A pipeline run over pieces of footage

Read with `docs/systems-review.md`, E2; with `docs/spec/what-a-node-declares.md`, which this
assumes; with `tools/region.py`, the cut in space; and with `sieve_player/bare.py`, the walk with
no window.

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
E2 has it: the scheduler and the farm, items made while the work runs, attributes as a general
store, and a second network.

## A bout walked alone

Assumes: nothing.

A stepped node's result at a row depends on where its walk began, so a tracker's identities in a
bout walked alone are not those of the same rows cut from a walk of the whole clip. TOPs and
Bonsai both answer alone.

- [ ] Kendrick: a piece's result is the piece walked alone, or the same rows cut from a walk of
  what it was cut from; this line says which.

## A piece's record

Assumes: A bout walked alone.

Facts to weigh. `tools/region.py:origin` is the step in space. `plan.py:Entry.piece` says which
cutting node a node's inputs are of.

- [ ] A piece carries the steps that cut it, each a range of rows or a rectangle relative to the
  piece above, and their sum on the footage.
  Check: a seam: a rectangle within a range within a rectangle sums to the footage's own pixels
  and rows.

## A tool that cuts in time

Assumes: A piece's record; `docs/spec/what-a-node-declares.md`'s A setting that changes no result
is in no key.

Facts to weigh. A `region` holds the shapes and a choice of one, and narrows the footage to it.
The tree sets the rows a document is walked over for a served clip alone. Not sized: how far a
node that is no served file setting those rows reaches into `plan.py` and `walk.py`.

- [ ] `period` holds a table of stretches and a choice of one, and what reads it reads the rows of
  that stretch, as what reads a region reads its rectangle. Its key is of the stretch chosen.
  Check: a seam: the keys below a period across a stretch moved that is not the chosen one, and
  across the chosen one moved.
- [ ] A period under a region and a region under a period both run.
  Check: a one-off over the crossings clip.

## A document walked with no window, under a named choice

Assumes: A piece's record; `docs/spec/what-a-node-declares.md`'s What is asked for is one set the
worker reads.

Facts to weigh. `bare.py` walks the clip under the choice the document holds, started by the
window. Part 4's H6: its decoder is told where the store is by a global the window alone sets.

- [ ] A command walks a document under a choice named for each cutting node, with no window, and
  writes what its `csv` nodes write.
  Check: a one-off: its csv equals the one the player writes of the same document and choice.
- [ ] A csv so written is in the footage's own pixels and rows, by its piece's record.
  Check: the same one-off, a record of a cut region read back against the plate.

## Every piece

Assumes: A document walked with no window, under a named choice.

- [ ] One command runs that one for every choice, the product of what each cutting node offers and
  of the videos its selector matches, each a process, and ends when all have.
  Check: a one-off over the purb document: a csv a piece, each equal to the one made by hand.
- [ ] A piece that fails is said with its choice, and the others finish.
  Check: the same one-off with one piece's geometry made to refuse.

## Not here

A scheduler. Pieces made while a walk runs. Tables of several pieces merged into one. Identity
across pieces.
