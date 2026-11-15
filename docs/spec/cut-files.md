# Cut files: a file is named by what it holds, lies in the store, and is never written over

Read with `tools/_cutfile.py`, which names, writes and lands the clips a cutting tool cuts; with
`tools/region.py`, the one cutting tool, and its `cut_file` and `cut_files`; with the rows of those
two facets in the root README's facet table, which are the whole of what the player knows of a cut;
with `sieve_player/store.py`, which says where the store is; and with `sieve_player/graph.py`, whose
`Graph.cut_file` and `Readers` serve a file.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

Words. A *cut file* is a video file holding a part of one footage. Its *extent* is which part: for
region, one rect at every row. Its *recipe* is how it was encoded: the quality and whatever of the
encoder's settings changes the bytes. Its *key* is a digest of the footage's print, the extent and
the recipe. A cut file *lands* when it is whole under its final name. The *store* is the one folder
cut files lie in, whatever video they are of.

## Why

Two regions on one video, each with a shape chosen, each served a clip of `<video>-crops/`. A Cut
pressed on one card wrote every shape's clip and held off that node alone; the other node's reader
had its clip open, Windows refused the replace, and the cut ended with "the clips did not land"
after the whole encode, the record already removed. With one node held off and the other serving,
`os.replace` over the first node's file succeeds and over the second's raises PermissionError. A
bare walk's process holds the clips open the same way and was told nothing.

The rule the tree enforced was that the node whose card was pressed serves nothing; the rule it
needed was that a file being written over is served by none. Naming a file by what it holds removes
the need for either: a shape that moved is another rect, so another name, which no reader can have
open because it is not there yet. Nothing is replaced, so nothing is held off, in this process or
another. Two geometry files' clips, two qualities of one shape and a moved shape's old clip then lie
side by side, and a nudge to one shape of five cuts one clip.

The plan already names a node's result this way, by a digest of what it was computed from, and the
memo holds under that name. A served node's key is the served file's own print, so what reads it is
keyed by the bytes that landed and not by the name: the name says what was asked for, the print what
was got, and two encoders' differing bytes for one key are two keys downstream.

A file that is never replaced is never removed either, and a folder beside each video is found again
only by whoever opens that video. One store holds every video's cut files where one control can show
what they take, and a video moved or renamed finds its clips by its print. Within the store a cut
file's own cuts lie in a folder under it: a cut of a cut is found by the print of the file it was
cut from, and that file cut again may land with other bytes, so what was cut of a file is of no use
without it and goes with it. Narrowing in space, in time and around an individual may follow one
another in any order and to any depth, and the folders follow whatever order it was.

Region cuts in space. A cut of detection periods cuts in time, and a cut around a tracked
individual has a rect that moves by the row. Each is a part of one footage under a recipe, and each
has problems of its own that are not this spec's. What is settled here is only that none of them
needs another way to name, land, find or place a file: an extent is the tool's to state, and the
naming reads none of it.

## A cut file's name is its key

Assumes: nothing.

- [x] A cut file is found in its footage's folder by its key and by nothing else. Its name is a
  label, a word for the reader that the first cut of that key gave it, and the key; the label names
  nothing, and a file renamed under its key is still found. The shape's outline and name, the
  geometry file's path and the node's id are not in the key. Two shapes of one rect are one file, as
  are two geometry files holding it.
  Check: a one-off under `docs/findings/experiments/`.
- [x] The extent is a JSON value that says what kind it is, and the key is the same however its
  members are ordered; the module that names a file reads the kind and nothing else of it, and names
  an extent of a kind no tool in the tree has.
  Check: `tests/test_cut_file.py`, a seam: one extent under two orders has one key, and a rect, a
  span of rows and a table of a rect a row have three.
- [x] The recipe holds the quality and the arguments the encoder is run with for it, a constant
  of the module's, so a file cut under another command is another file.
  Check: `tests/test_cut_file.py`, with the box above: the key moves with the quality and with the
  constant.
- [x] `region.cut_file` answers the path its footage, the chosen shape's rect and the node's quality
  name when a cut file has landed there and the node's `serve clip` is on, and None otherwise: a
  moved shape, another quality and another footage are each a file not yet cut, and the card says
  the chosen shape's clip is not cut. With `serve clip` off the node runs whatever the store holds,
  its clips are still among those `cut_files` names, and the card says the clip is not served. No
  record of the folder is read to decide it.
  Check: `tests/test_cut_file.py`, in place of the test of region's answer off its record.

## A landing writes no name that exists

Assumes: A cut file's name is its key.

- [x] A Cut writes the clips its shapes name that have not landed, and only those, in one pass; with
  every one landed there is nothing to cut and the card says so. A clip is written under a name of
  its own that is no cut file's and takes its final name once whole, by a step that fails where a
  file has that name: the file there is left as it is and the new clip is dropped. A key a Cut of
  the same process is still writing is not written by another.
  Check: `tests/test_cut_file.py`, an invariant: over a stand-in for the encoder, every path that
  existed before a Cut began has the bytes it had when the Cut ends, landed, failed or cancelled.
- [x] A sidecar beside each cut file says its footage, extent, recipe, label and size in bytes. It
  is written whole and takes its name after the cut file has its own, so a sidecar is only ever
  beside a cut file its own writer landed. A cut file is served while it is the size its
  sidecar says, and one whose sidecar is gone is served with its size unchecked, the name being its
  identity. The sidecar is never read for which file a node serves.
  Check: `tests/test_cut_file.py`, with the refused size it holds already.
- [x] Nothing holds a node off its file: `Graph.hold_off` and `Graph.without`, the `cutting` signal
  and what the pane and the window keep of it, and a landing's wait on an open reader are gone, and
  the README's facet row says nothing of them. A node serves the clip a Cut landed for it once the
  Cut ends, with nothing else pressed. A Cut is handed each piece as a label, an extent and the
  encoder's arguments that keep that part, and reads nothing of the extent.
  Check: `tests/test_cut_file.py`, a seam: two nodes each serving a clip of one folder, both read, a
  shape of one moved, and the Cut for it lands while both readers are open.
- [x] A Cut still ends with its card, and at the interpreter's exit, leaving no cut file that is not
  whole.
  Check: the invariant above, cancelled.

## The store

Assumes: A cut file's name is its key.

- [x] The store's folder is the one the user chose, else `SIEVE_STORE`, else a folder of the
  player's own; a choice outlives the launch, and a folder that cannot be written is refused with
  the reason and the choice stands as it was.
  Check: `tests/test_store.py`, a seam.
- [x] A video's cut files lie in the store under its footage's print, wherever the video lies and
  whatever it is called, and a cut file's own cut files lie in a folder beside it named by its key,
  to any depth. No test reads or writes the user's store.
  Check: `tests/test_cut_file.py`, a seam, and the fixture every test runs under.
- [x] The header shows the store as one control: the bytes it holds against its disk, its folder
  under the pointer, and a press that chooses another. The cutting nodes are asked again of a store
  just chosen, and the files of the store before it stay where they were.
  Check: a one-off under `docs/findings/experiments/`.

## What the store holds that nothing uses

Assumes: A landing writes no name that exists, The store.

- [x] The clips of a cutting node's footage that no cutting node of the open document names, under
  any choice its params allow, are counted on that node's card with their size, what was cut of them
  in it, and deleted on a press with what was cut of them, beside a line saying that another
  document may use them. A tool says what its node names by a `cut_files` facet beside `cut_file`,
  and the player hands every card the union. A file a reader of the player's has open is not among
  them; one another process has open stays at the press, and the card says so. A card that wrote or
  removed files of the store says `storeChanged`, its params as they were, and the player reads the
  store and asks the cutting nodes again.
  Check: a one-off under `docs/findings/experiments/`.

## Not here

A cut that keeps some of the footage's rows and not all. `Graph._compute` takes a served file's end
for the plate's, and the walk, the timeline and the held results take a served row for the plate's
row of that number; both hold of region's cut and of no cut in time. The extent in the sidecar is
where a later reader finds which rows a file holds.

A tracked cut's extent, a rect a row over a whole clip: how large it is to state and to digest, and
whether it is stated or named by the key of the node that found it.

One file for one part of the plate reached two ways. A region reading a period's file and a period
reading a region's file hold the same pixels under two footages, so two keys in two folders.

Housekeeping over the whole store: a limit on its bytes, what was served longest ago going first,
which documents use a file, and the files of footage no open document reads. The clips cut beside a
video before there was a store, under `<video>-crops/`, which nothing reads.

Moving a store's files to a store chosen after it.

The words crop, cut, clip and piece.
