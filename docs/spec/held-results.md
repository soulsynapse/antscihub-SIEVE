# Held series: what a walk computed for the series chain is kept, written beside the document in a quiet moment, read back when it opens, and shown on the strip

Written 2026-11-13 on v5-held, over the longer spec of 2026-11-12 under this name, which git has at
a7ceace5. Kendrick's word of the 13th narrowed it: the series chain's results are persisted, a window
moved about among them, beside the document, and open between sessions; a result that what is upstream
of it has made stale is not served, and nothing more is owed it; and the strip says where a jump costs
nothing. Read with `sieve_player/held.py`, the file and what a run is; with `sieve_player/window.py`,
whose `runs` are what is held and whose `_run_over` is what serves a window from them; with
`sieve_player/worker.py`, whose `_Walk.spared` is a window walked with no chain run; and with
`docs/findings/2026-11-12-what-a-walk-holds.md` for what a series result weighs.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

Words. A *run* is one walk's results for every chain node over the rows it walked, from its first row.
A window is *served* when its results are cut from a run and the chain is not run over it.

## A walk's results are held, and a window on held rows is served

Assumes: nothing.

Facts to weigh. A window moved ten rows drops its whole result, and a clip walk's rows are read by the
strip alone (the 2026-11-12 spec's Why). A result carries the key its node had as the chain ran
(`worker.run_chain`); a key is the node's tool, its params, its band and the keys upstream, the video's
path and the decoder's output at the root (`plan.key_of`, `plan.base_key`). A stepped node's value at a
row can depend on the row its walk began at, `track`'s ids and its first rows among them
(`docs/findings/2026-11-13-a-windows-tracks-against-the-clips.md`), so rows of two walks are not stitched.
The window walk's rows also feed the display, the densities and the frame tools' draws.

- [x] A window walk that reached the window's last row, and a clip walk that reached the clip's, are
  each held as a run as they end, a run let go when another covers its rows with every node it has
  under the same key, a window walk given held rows not held at all, since its run would hold them a
  second time, and none let go for room until
  the runs together pass one named bound of bytes (`window.HELD_BYTES`), the oldest then first.
  Check: `docs/findings/experiments/2026-11-13-held-series.py`.
- [x] A window that lies wholly inside one run whose every chain node has the key and row space it has
  now is served from it, from the run that began earliest: the results are the window's at once and
  no chain is run over it. Its frames are walked as any window's are, so a move or a drag of the
  playhead inside it shows each row from the memo
  (`docs/findings/2026-11-13-a-served-window-jumped-about.md`).
  Check: the same one-off moves a window away and back and reads no step of the chain and the
  window's frames in the memo, then selects a frame node and reads its field.
- [x] A window inside a run that has some of the chain's stepped nodes under the keys they now have,
  and not all, is walked with those given: the rest is stepped from them, a given node is not stepped
  again, and where every head is given no row of the window is walked for the chain. So a node added
  under one already held reads what is held. A clip walk is given what a run over the whole clip
  holds in the same way, a series bake's too, and one given every stepped node and every head ends
  in a turn.
  Check: the same one-off adds a node under `track` in the second window, walks the clip for it, and
  asks for the clip again.
- [x] A run under a key the chain has left serves nothing, and serves again when the key returns.
  Check: the same one-off turns a knob and turns it back.

## The runs are beside the document

Assumes: A walk's results are held.

Facts to weigh. A key sees neither the footage's bytes nor a tool's code. A document knows its path once
saved, and one never saved has none.

- [x] The runs held are in one file beside a saved document, a record a run, each run in it whole or
  not at all, written off the GUI thread once nothing new has been held for a moment and again as the
  video closes; a document saved afterwards gets the file at the save. A run is pickled once: one
  held since the file was written is added behind those it has, and when a run the file has is no
  longer held the file is made again from the kept records' bytes (`held.File`). A row's table that is every row's dtype is in the file as one
  table and the rows' lengths (`docs/findings/2026-11-13-what-the-held-file-costs.md`).
  Check: the same one-off, which cuts the file short in its last record and reads the runs before it.
- [x] Opening the document holds the file's runs: its first window is served where one covers it, and
  the strip draws a clip run's signals with no clip walk asked.
  Check: the same one-off, in a second window.
- [x] A file made under other footage at the path or under other tool files, or one absent or
  unreadable from its first bytes, is the same as none.
  Check: `tests/test_held.py`.

## What is held is shown

Assumes: A walk's results are held.

- [x] The strip draws a bar over the rows of every run that would serve a window now, so a stretch a
  window can be placed in for nothing is told from one that will be walked.
  Check: the same one-off reads the bar after two moves, after an open, and under a turned knob.
- [x] The strip draws a shown node's signal over every run held under the key the node now has, the
  selection's in its colour, a node's stretches on one scale, and no row twice: where runs lie over
  one another the rows are drawn from the one that would serve them, and the bar is their union.
  Check: the same one-off reads the stretches drawn after two moves.
- [x] The card of a series node whose window has a result says about how many bytes that node's result
  over the whole clip would add to the file, from the rows walked.
  Check: the same one-off reads the line against a clip run's size.

## Not here

A window that straddles two runs, or reaches a row past one, is walked whole: rows are not stitched, by
the fact above, and no tool says whether its rows would stitch soundly. A served window is spared its chain and not its frames. The cap, a table's release and the count's fix,
all of the 2026-11-12 spec, are dropped. The player's own code is not in what a file is good under, only
the tools'. A frame node's card says nothing of a disk.
