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
cutting node a node's inputs are of. `region.py:run` refuses a frame that is not its file's
plate, so no document holds a rectangle within a rectangle; a region reading a piece is not
here.

- [ ] A piece carries the steps that cut it, each a range of rows or a rectangle relative to the
  piece above, and their sum on the footage.
  Check: a seam: a rectangle within a range, and a range within a rectangle, each sum to the
  footage's own pixels and rows.

## A table written is in the footage's own pixels and rows

Assumes: A piece's record; `docs/spec/what-a-node-declares.md`'s What a wire carries is in one
table. Changes what a csv below a region holds.

Facts to weigh. A csv written below a region is in the cut clip's pixels, so two regions' tables
cannot be laid side by side or drawn over the footage. A piece's record holds cuts and no scale:
`rescale` and `coarsegrain` hand out a plane of another size than the piece's, and a table's
dtype carries the plane it was found in, `tools/_table.py:plane`. What a column is in is said
where it is minted and carried on the dtype, in the units the wire table has; one minted with
none is in no plane's pixels, and one the dtype says nothing of may have lost its unit
(`docs/findings/2026-11-17-what-keeps-a-dtypes-metadata.md`). A csv on disk written before this
has no word of a piece on its key line. `csv.py:default_name` is the footage's stem and the rows, and the
footage of a node below a region that serves no clip is the plate, so two such regions of one
video name one file.

- [ ] A csv's rows are the footage's by its piece's record, and each column that says a unit is
  in the footage's pixels, scaled along its axis by the plane it is of against the piece's size
  and, a position, moved by the record; a column that says none is written as it is; whoever
  writes it. Its name says the piece, and its key line says it always, the plate where the table
  is of no cut, so a line with no word of a piece is a file written before this.
  Check: a one-off: a csv written below a region, and one below a region and a `rescale`, their
  positions read back against the plate; one below an `attach`, its mark's area against the
  mark's plane; of two regions of one video that serve no clip, two files; and one of the plate,
  its key line saying so.
- [ ] A table with a numeric column its dtype says nothing of is not written: the write raises,
  naming the column.
  Check: `tests/test_csv.py`, a seam: a table one column of which has no entry, handed to the
  write.

Worth a look: a csv of the purb document before and after, since what reads one downstream reads
other numbers.

## A document's path inputs are loaded with no window

Assumes: nothing. Changes no key.

Facts to weigh. `window.py:PlayerWindow._pick_paths` is the one place a tool's `PATHS` loader is
run and its params laid on the node. `bare.py` is handed the document as the window holds it,
the loaders' params already in it, so it walks under the video the window has open and no other.

- [ ] What picks each path input's file and lays its loader's params on the node imports no Qt,
  and the window's is that and no second copy.
  Check: a one-off: the purb document loaded with no window holds the params the player's does;
  `tests/test_seams.py`, a seam, that `window.py` calls no loader of `PATHS` itself.

## A document walked with no window, under a named choice

Assumes: A table written is in the footage's own pixels and rows; A document's path inputs are
loaded with no window; `docs/spec/what-a-node-declares.md`'s The registry is the one reader of
what a tool declares.

Facts to weigh. `bare.py` walks the clip under the choice the document holds, started by the
window, and drives its walk itself with no worker. Part 4's H6: its decoder is told where the
store is by a global the window alone sets. What a `csv` node writes is `csv.py`'s `write` under
its `default_name`, called by `tools/_csvfile.py:widget` and no facet; where it writes is that
widget's `_path`, which with `beside footage` off is a dialog's answer. What a region offers is
`region.py:crops`, no facet either. `plan.py` takes a cutting node to be one whose tool has
`cut_file`, and a tool that cuts in time serves no file.

Open: whether the command is `bare.py` handed a choice or a second walker beside it.
Recommended, and a session may build on it: one, which the window starts as it starts `bare.py`.

Open: where a `csv` node with `beside footage` off writes with no window. Recommended, and a
session may build on it: under a folder the command is given, and with none the command refuses
the document, saying the node, before a row is walked.

- [ ] A command walks a document under a choice named for each cutting node, with no window, and
  writes what its `csv` nodes write.
  Check: a one-off: its csv equals the one the player writes of the same document and choice.
- [ ] What the command calls of a tool, to write and to learn what a cutting node offers, is a
  facet the registry's table lists, and a cutting node is a node whose tool has the one that
  says what it offers: `plan.py`'s `Entry.piece` and the command take it by that.
  Check: the seam of the registry as the one reader, which stands; the baseline of
  `docs/spec/what-a-node-declares.md`, compared.
- [ ] The command's decoder keeps and reads a file's frame times in the store as the player's
  does.
  Check: the same one-off over a transport stream, `00000.MTS`.

## Every piece

Assumes: A document walked with no window, under a named choice.

Facts to weigh. A geometry file is a video's, so what a region offers is known under a video and
not before it. A process a piece decodes the plate once a piece wherever its region serves no
clip. A document may hold cutting nodes side by side, none below another, each above a `csv` of
its own: the product over those walks every `csv` once for each choice of a node it is not below,
and `tools/_csvfile.py:replace` writes through `<path>.part`, so two processes writing one file
meet there. `region.py`'s `serve clip` is on by default, and with it on, a shape chosen and no
clip of it in the store, `region.py:cut_file` raises and the node does not run; the region's card
alone cuts, every shape of the node in one ffmpeg pass, through `tools/_cutfile.py:Cut`, which
imports no Qt and is polled.

Open: how many pieces are walked at once. Recommended, and a session may build on it: a count the
command is given, one where none is.

Open: which cutting nodes the command ranges over. Recommended, and a session may build on it:
those it is told, each other keeping the choice the document holds; told two of which neither is
below the other, it refuses before a row is walked, saying both.

Open: what the command does of a clip a choice is to serve and the store lacks. Recommended, and
a session may build on it: it cuts them, a pass a video, before a piece of that video is walked.

- [ ] One command runs that one for every choice: for each video its selector matches, the
  product of what each cutting node it ranges over offers under that video, those nodes lying
  one below another; each a process, no two writing one file, and it ends when all have.
  Check: a one-off over the purb document: a csv a piece, each equal to the one made by hand;
  and over a document of two regions side by side, as many walks as the one ranged over offers.
- [ ] No piece is refused for a clip that is not cut: under each video, what the choices are to
  serve and the store lacks is there before a piece of it is walked.
  Check: the same one-off with the store holding no clip of the video.
- [ ] A piece that fails is said with its choice, and the others finish.
  Check: the same one-off with one piece's geometry made to refuse.

## A bout walked alone

Assumes: nothing.

A stepped node's result at a row depends on where its walk began, so a tracker's identities in a
bout walked alone are not those of the same rows cut from a walk of the whole clip.
`held.py:Runs.over` answers today by cutting a range from the run that began earliest, and
`held.py:Runs.from_first_row` takes the run from row 0 over any other, both leaning to the
second answer. TOPs and Bonsai both answer alone. The player's window is served by `Runs.over` too,
called in `window.py` with the window's rows, so whichever rule a piece is held to, the window is held to it
unless it is said to be no piece: under alone a window moved within a held walk of the clip
walks its stepped nodes again, and under the other only a run from the piece's first row serves
it.

- [ ] Kendrick: a piece's result is the piece walked alone, or the same rows cut from a walk of
  what it was cut from; this line says which.
- [ ] Kendrick: the player's window is a piece and held to that answer, or is a view of the
  clip's rows that any held run may serve; this line says which.

## A held run serves what a piece's result is

Assumes: A bout walked alone.

- [ ] A stepped node's held rows are served for a piece's range only where they are what the
  first answer above says that range's result is, and for the window's as the second says.
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
