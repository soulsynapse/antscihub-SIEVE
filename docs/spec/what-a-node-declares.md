# What a node declares, the key made of it, and what goes by that key

Read with `docs/systems-review.md`, E1 and E3 and the cut's line on C9; with `sieve_player/plan.py`,
which makes every key; with the registry's facet table (`python -m sieve_player.registry`); with
`tests/test_seams.py`, which says what may import what; and with
`docs/findings/2026-11-16-which-settings-no-run-reads.md`, which lists the places that answer
whether a thing is still good by a rule of their own.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

## Why

Toggle `outline` on a track node and everything below it is walked again. Edit a comment in any
tool and every document's held file serves nothing. Move a card while a bare walk runs and its
results are dropped. Each is a different rule answering one question, whether a result is still
good, and their being several is why what a change empties reads as random. Kendrick, reading the
ledger: keying "was supposed to be more or less universal", and the candidates the review merged
as E1, with pull beside them, "all seem to want a key-like or universal interface for what needs
to get done next".

The programs SIEVE stands among have that interface, and this spec is theirs with nothing added.
Nuke's Op is the one followed, part for part and in its order:

| Nuke's Op | here |
| --- | --- |
| A node declares its knobs, once; the panel is made of them | A param is declared once |
| The hash is the inputs' hashes and every knob but those flagged as not rerendering; a node may append to it | The key, of what is declared; `key_params` stands where append does and answers in place of the params, where append adds |
| The Viewer and the disk cache use the hash as their key directly | A kept result, and a job, goes by the key |
| `_validate`: what the node hands out, said before a pixel is computed | What a wire carries, in one table |
| `_request`: the node is told what is wanted of it | The display says which draws it paints |

Nuke reads all of it off the Op and nowhere else, which here is the registry. A tool stays a module
of attributes: no class is inherited.

It is a large rework of small parts. Every deliverable says whether it changes a key, what is
served or what a tool raises; one that changes none is held to the plan printing what it printed,
and the two that change what is kept or served each wait on a deliverable that is Kendrick's
alone.

## The plans as they stand

Assumes: nothing.

What every later deliverable is compared with.

Facts to weigh. `__main__.py:show_plan` hands `plan.py:plan` no `cut_file`, so under `--plan` no
node serves a file and the key of one that does in the player is not printed.

- [x] `docs/findings/` holds what `python -m sieve_player <document> --plan` prints for each
  document under `video-tests/`, with the commit it was printed at.
  Check: the file is there, a table a document.
- [x] Beside it, for each of those documents a node of which serves a file in the player, every
  node's key as the player's graph plans it under the store as it stands, and beside each served
  node the file it serves, so a key a clip cut or deleted since has moved is told from one a
  deliverable moved.
  Check: the file is there, and a served node's key in it is not the one `--plan` printed.

## The registry is the one reader of what a tool declares

Assumes: The plans as they stand. Changes no key.

Facts to weigh. Part 5's A2 lists the modules that find out for themselves what a tool declares.
The registry imports nothing of the player. `tests/test_seams.py:MAY_IMPORT` has `document`
importing nothing, and `document.py`'s readers of a tool are there for that. `EXPECTS` is a string
or a tuple and is made a tuple in more than one place. The player calls a tool's `run`, `step`,
`fold`, `draw` and `pick`; a call of a facet the registry answered is no reading of the tool. What
a settings widget may have, the registry's `WIDGET_FACETS`, is looked for on the widget and is not
this deliverable's. The registry hands out `probe(tool, facet)`, which no module but the registry
calls, and a module that called it would find out for itself as one calling `getattr` does.

- [x] No module under `sieve_player/` but the registry finds out what a tool declares, whether it
  has a facet or what a facet that is data holds; each asks the registry, by a name that says what
  is asked.
  Check: `tests/test_seams.py`, a seam: outside the registry no `getattr` or `hasattr` names a
  facet of `FACETS`, no facet that is data is read as an attribute of a tool, and nothing calls
  the registry's `probe`.
- [x] `document` and the modules that read a tool may import the registry, and
  `tests/test_seams.py` says so; the registry still imports nothing of the player.
  Check: the suite.
- [x] What a tool expects is made a tuple in one place.
  Check: a grep.
- [x] Every document's plan prints what it printed, and its keys in the player are what they were.
  Check: the baseline, both tables compared.

## A param is declared once

Assumes: The registry is the one reader of what a tool declares. Changes no key and nothing a tool
raises.

Facts to weigh. Part 5's A11: a param's default, its row in `settings`, a check where it is
computed and a fallback where it is read. `ParamWidget.add_int`, `add_float`, `add_bool`,
`add_text`, `add_choice` and `add_list` are the kinds of row there are. `region.py`, `file.py` and
`inrange.py` have a card of their own. `Document.resolve` lays a node's params over `DEFAULTS`, so
a fallback where a param is read restates what the node already holds. A tool imports the player
inside `settings` alone, and its computing runs with no player. A declaration is read where no
widget is, a walk with no window checking a choice it is handed, so what it says of a param is
the kind of its value, and the row is the player's to make of that. `registry.discover` makes a
module that does not import an entry with its error and no crash.

Open: the form of a declaration. Recommended, and a session may build on it: plain values of the
language, as `DEFAULTS` is, that a tool writes with no import, so a tool's module still loads and
computes with no player.

- [x] A tool declares each param in one place: its name, its default, the kind of its value, and
  its range or its choices. A tool with a card of its own declares its params as any other does,
  one that is no row of a plain widget by its name and default alone. The registry's table lists
  the facet with its hint.
  Check: `tests/test_registry.py`, the facet read from the table.
- [x] A declaration the registry cannot read is its tool's entry's error, as a module that does
  not import is.
  Check: `tests/test_registry.py`.
- [x] A tool's defaults and its plain settings widget are made of that declaration by the player;
  no tool has a `DEFAULTS` of its own, and none with a plain widget a `settings`. A tool with a
  card of its own keeps its `settings`.
  Check: a one-off that builds every tool's widget offscreen at the commit before and at this one
  and compares, a tool at a time, the names in order, each row's kind, range and choices, and
  `params()`.
- [x] No tool restates a default where it reads a param.
  Check: a grep for the fallbacks A11 names.
- [x] Every document's plan prints what it printed, and loads to the params it loaded to.
  Check: the baseline, compared; a one-off over the documents for the params.
- [x] What a tool raises for a param it refuses, and where, is as it was.
  Check: a one-off: every tool that refuses a choice, handed one it does not offer, raises the
  text it raised.

Worth a look: a tool's card in the player beside the same card on v5.

## What a wire carries is in one table

Assumes: The registry is the one reader of what a tool declares. Changes no key.

Facts to weigh. Part 4's H17: what lies on a `blobs` or a `tracks` wire is defined under `tools/`,
and the player knows it by its shape in `graph.py:nbytes`, `graph.py:gated` and `walk.py`.
`document.py:OVERLAYABLE` is a list of names. What a tool may import of the player is
`tests/test_seams.py`'s `TOOLS_MAY_IMPORT` and `TOOLS_MAY_TAKE`, which are not
`sieve_player.__all__`. A table's dtype carries the plane it was found in, `_table.py:plane`, and
`csv.py:fields` writes every numeric column, nothing saying which of them are in that plane's
pixels. A column's name is a tool's to mint and some are made of a param: `attach.py` adds
`<prefix>_<column>`, `sample.py` the column its param names, `kinematics.py` `dx`, `dy` and
`speed`, which scale with a plane and are no position in it; `attach.py`'s area is in the mark's
plane's pixels and not the table's. `_table.py`'s header has what a column means as the tool's
that computes it. So no table of the player's can list the columns, and what one is in is said
where it is minted. `registry.types` takes the set of types from what the tools name, so a type
is a tool's to coin today. A dtype's metadata is lost with no error by a concatenate of two that
differ, by several fields taken and by a dtype made again of its `descr`, and
`_table.py:_plane_dtype` makes one of `descr` and the plane alone
(`docs/findings/2026-11-17-what-keeps-a-dtypes-metadata.md`); so a column whose dtype says
nothing of it may be one whose unit was lost.

- [x] One table under `sieve_player/`, importing no Qt and among what `tests/test_seams.py` lets a
  tool import, says of each type a wire carries its name, whether it is a table a row, how its
  bytes are counted and whether it can be overlaid, and says the units a column of a table may be
  in: a position along x or along y, a length along x, along y or along neither, an area, each of
  a plane's pixels. It names no column. The player reads these of the table and of no result's
  shape; `tools/_table.py` reads the same table.
  Check: a grep for the shape tests H17 names.
- [x] A type a tool produces or expects is a type of the table, so a new one is added there
  first, where a tool coined it.
  Check: `tests/test_seams.py`, a seam, that a tool's `PRODUCES` and `EXPECTS` name types of the
  table.
- [x] A column's unit is said where the column is minted and carried on the table's dtype as its
  plane is, with the plane it is of where that is not the table's; a column minted with none is
  in no plane's pixels, and none is on the dtype as a unit is, so a column the dtype says nothing
  of is told from one minted with none.
  Check: `tests/test_seams.py`, a seam: no column is added under `tools/` with its unit left
  unsaid, none being a thing said; a one-off: the unit of every column of a table below `blobs`,
  `track`, `kinematics`, `attach` and `sample`, read back off its dtype, none among them and no
  column unsaid.
- [x] Every document's plan prints what it printed.
  Check: the baseline, compared.
- [x] The table has a unit for a column of points, (N, 2) x, y each of a plane's pixels. Observed
  building the box of units: `contour` is such a column, in the plane's pixels and in none of the
  six units, and minted with none it would read as in no plane's pixels.
  Check: the one-off of the units, `contour` among them.

## A draw named as wanted

Assumes: nothing.

`Graph.drawing` takes the overlay's to be every fed frame node whose tool has a `draw`. The
document has a display flag and an overlay flag; the pins are the plot's and name signals.
Kendrick: "sometimes I want a draw on the video that is hard to surface as something needing it".

- [x] Kendrick: a draw is named as wanted by a list in the document, as a signal is by `pinned`.
  Neither flag names it: each is one node, and the overlay flag's is a plane heated over the
  frame and no tool's `draw`.

## The display says which draws it paints

Assumes: The registry is the one reader of what a tool declares; A draw named as wanted. Changes
no key.

Facts to weigh. `Graph.watch` is told what the plot shows, and the worker folds for those and no
other.

- [x] The document holds the nodes whose `draw` is wanted in a list saved as `pinned` is, and a
  node's header puts its node on the list and takes it off; a node removed is off it.
  Check: `tests/test_document.py`, beside the seam of `pinned`.
- [x] A document saved with no such list loads with every node whose tool has a `draw` on it, and
  paints as it did.
  Check: `tests/test_document.py`, the same seam.
- [x] The display tells the graph the nodes of the list whose `draw` it paints, as the plot tells
  it what it shows, and the worker computes at the row for those and no other.
  Check: a seam beside the test of `Graph.watch`: a fed frame node with a `draw` that the display
  does not name is not computed for the frame.
- [x] A node placed on the canvas whose tool has a `draw` is on the list, and a list of no
  nodes is saved as one, where `pinned` of none is left out of the file. Observed building the
  boxes above: a file with no list is every `draw`, so none wanted has to be told from none
  said; and a placed node painted its `draw` before there was a list.
  Check: a one-off: a flag put out in the player, the file saved, opened again, and opened with
  its list cut out.

## A job goes by the keys it computes under

Assumes: nothing. Changes when a bare walk's results are kept.

Facts to weigh. A read, a walk and a cut are each ended when their own key moves
(`18c2010a`, `36e3565e`, `a603747b`). `window.py:PlayerWindow._bare_said` drops a bare walk's
results where the document is not, whole, the one the walk began under.

- [x] A bare walk is ended, and its results dropped, when the key of a node it walks has moved and
  by no other change to the document.
  Check: a seam: a function of the keys the walk began under and the plan now answers whether it
  stands, and stands across a moved card, a node added off the chain and a param that is in no
  key.

## A csv names its footage by its print

Assumes: nothing. Changes a csv's key line.

Facts to weigh. `tools/_csvfile.py:key_line` names footage by a file's name, where the memo, the
held runs, a cut clip and a table of frame times name it by `decoder.footage_print`. The line's
key already holds that print, `plan.py:base_key` being made of it and a served node's key of its
file's; `_csvfile.py:written_key` says whether a file is stale by the key alone; and nothing
under `tools/` or `sieve_player/` reads `footage=` back. The name is the one part of the line a
person reads.

Open: whether the name stays on the line beside the print. Recommended, and a session may build
on it: it stays, as a field of its own that nothing compares.

- [x] A csv's key line names its footage by `decoder.footage_print`.
  Check: a one-off: a csv written of a clip and of a copy of it under another name carry one
  key and one print.

## Held results and an edited tool

Assumes: nothing.

`held.py:stamp` holds a digest of every file in the tools' folder, and `held.py:File.load` answers
no runs under another, so an edit to any tool lets go of every document's held file. Kendrick: a
kept result does not go by a tool's code. Nuke's hash holds no plugin's code and a cache there is
cleared by hand; a plugin there changes at a release, and a tool here is edited most days. Without
the digest a result held before a tool was edited is served after it, looking as a fresh one
does, until it is let go by hand. The review rates a stale result served as the kind that matters
most. The digest is taken when the window opens, and a bare walk's process imports the tools as
they lie when it starts, so a bare walk's results are already held under a digest of code that
did not make them. `held.py:File.load` answers no runs of a file whose stamp is not the one it is
handed, so a stamp of another form lets go of every held file once unless the form it had is
still read.

- [x] Kendrick: held results outlive an edit to a tool, are served, and are let go by hand; the
  node says they are stale and the user decides. A `!` stands in the node's header beside the
  tool's name, where a series' size tag stands, on a node whose held runs were made under other
  code of its tool than lies there now and on every node below one. The code is a tool's own and
  not the folder's, so an edit to one tool marks no node of another.

## A held file goes by the key alone

Assumes: Held results and an edited tool. Changes what is served after a tool is edited.

- [x] A held file written before this, under the stamp with the tools' digest, serves its runs.
  Check: a one-off: a held file of `video-tests/` as it lies, its runs read back.
- [x] The player lets go of a document's held results at a word from the user.
  Check: a seam: after it, `File.load` answers no runs.
- [x] What a held file is good under holds nothing of the tools' code: an edited tool leaves a
  document's held runs serving.
  Check: a seam: a held file written, a tool's file touched, the runs read back.
- [x] A held run carries a digest of the code it was made under, its tool's file and the files
  of that folder whose name begins with an underscore, taken in the process that walked it. No
  run is served or refused by it.
  Check: a seam: a run held and its tool's file touched, the digest it carries is not the tool's
  now; another tool's file touched, it is.
- [x] A node whose held runs carry another digest than its tool's now, or none, and every node
  below one on the chain, has the `!` in its header; a node with nothing held has none.
  Check: a seam: a function of the digests held and the plan answers the nodes marked, a node
  below a marked one among them and a node of another tool not.
- [x] A held result says the code of every node above it whose tool ran to feed it, a frame
  node's among them, and such a node whose tool's code is another now has the `!` and every
  node below it. Observed building the boxes above: a frame node holds no runs, so by its own
  runs an edit to `blobs.py` marks nothing while every result held below it is stale. Nothing
  is said of a node that serves a file, nor above one: its tool did not run.
  Check: the seam of the nodes marked, a node above the chain among them.

## Keys that move once

Assumes: nothing.

A param out of a node's key moves the key of that node and of everything below it, once, and a
held file's runs under the old keys are found by nothing and walked again.
`docs/findings/2026-11-16-which-settings-no-run-reads.md` has which params those are as the tools
stand.

- [x] Kendrick: yes. It is said before it lands, and the held files of the documents in use are
  walked again.

## A param that changes no result is in no key

Assumes: A param is declared once; Keys that move once. Changes keys.

Facts to weigh. `key_params` stands where Nuke's append does: what a tool says of its key where a
mark on a param cannot, `region.py`'s rect, or a param read only under some value of another.
`plan.py:keyed` keys a node by what it answers in place of the node's params, where append adds
to the hash. What a node hands out is its tool's `run`, `step` and `fold`, and for a node that
serves or picks a file its `cut_file` or `select`. A param in no key moves no key when it is
changed, so nothing is computed again for it. A tool with a `key_params` and a marked param says
one thing twice, and `plan.py:keyed` keys a node whose `key_params` raises by the whole of its
params, the marked among them.

- [x] A param's declaration says whether it changes what the tool's computing hands out, by any
  of those, and one left unsaid does.
  Check: `tests/test_registry.py`.
- [x] A node's raw key holds what `key_params` answers, in place of its params, for a tool that
  has one, and for any other its params that change the result; a param declared to change
  nothing is in no key, that of a node whose `key_params` raises among them.
  Check: `tests/test_graph.py`, the seam of keys extended.
- [x] Kendrick, at the build: a declaration alone is trusted, and a param a tool comes to read
  after declaring it to change nothing serves results of the value before. A param declared to
  change nothing is not in the params the player hands a tool's `run`, `step`, `key_params`,
  `cut_file`, `cut_files`, `select` or `matches`; `draw`, `pick` and the card are handed every
  param. So no result follows such a param, a tool that reads one where it computes raises, and
  `key_params` answers the same under any two values of one. This stands where two boxes stood,
  that `key_params` answers the same and that the computing hands out equal results under two
  values of such a param, each a check of one input.
  Check: `tests/test_seams.py`, a seam: no call of a computing facet in the player is handed a
  node's whole params, and every tool that declares such a param computes of the params without
  it; `tests/test_graph.py`, a run handed none.
- [x] A change to a param in no key is drawn at the row shown.
  Check: a one-off: `outline` changed on a track node, the frame painted with the other outline
  and no row computed.
- [x] `outline` of `blobs`, `filter` and `track`, and `csv`'s `beside footage`, are declared to
  change nothing; `attach`'s `outline`, which its `run` reads, is not.
  Check: the baseline's one-off against the finding: the keys that differ are those of a node of
  these four tools and of every node below one.

## Not here

A tool's code in a key. A class a tool inherits. A surface held still across versions. A range
checked where a tool computes. One place a failure is said, the review's E4. The window's memory
of a path loader's file, which keeps no result.

Which held run serves a range. `held.py:Runs.over` cuts a range from the run that began earliest,
so a stepped node's rows under one key differ by what is held; that rule is no key's and is
`docs/spec/pieces-of-footage.md`'s, behind the question it opens on.

What is asked for as one set the worker reads, the review's second part of E3. `worker.py:Worker._turn`
is a ladder whose order is read in one function, and the review watches it. What turns it is a
reader the ladder has no rung for; a walk with no window is none, `bare.py` driving its walk
itself.
