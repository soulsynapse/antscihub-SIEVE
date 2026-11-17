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
| The hash is the inputs' hashes and every knob but those flagged as not rerendering; a node may append to it | The key, of what is declared |
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

- [ ] `docs/findings/` holds what `python -m sieve_player <document> --plan` prints for each
  document under `video-tests/`, with the commit it was printed at.
  Check: the file is there, a table a document.

## The registry is the one reader of what a tool declares

Assumes: The plans as they stand. Changes no key.

Facts to weigh. Part 5's A2 lists the modules that find out for themselves what a tool declares.
The registry imports nothing of the player. `tests/test_seams.py:MAY_IMPORT` has `document`
importing nothing, and `document.py`'s readers of a tool are there for that. `EXPECTS` is a string
or a tuple and is made a tuple in more than one place. The player calls a tool's `run`, `step`,
`fold`, `draw` and `pick`; a call of a facet the registry answered is no reading of the tool. What
a settings widget may have, the registry's `WIDGET_FACETS`, is looked for on the widget and is not
this deliverable's.

- [ ] No module under `sieve_player/` but the registry finds out what a tool declares, whether it
  has a facet or what a facet that is data holds; each asks the registry, by a name that says what
  is asked.
  Check: `tests/test_seams.py`, a seam: no `getattr` or `hasattr` naming a facet of `FACETS`
  outside the registry.
- [ ] `document` and the modules that read a tool may import the registry, and
  `tests/test_seams.py` says so; the registry still imports nothing of the player.
  Check: the suite.
- [ ] What a tool expects is made a tuple in one place.
  Check: a grep.
- [ ] Every document's plan prints what it printed.
  Check: the baseline, compared.

## A param is declared once

Assumes: The registry is the one reader of what a tool declares. Changes no key and nothing a tool
raises.

Facts to weigh. Part 5's A11: a param's default, its row in `settings`, a check where it is
computed and a fallback where it is read. `ParamWidget.add_int`, `add_float`, `add_bool`,
`add_text`, `add_choice` and `add_list` are the kinds of row there are. `region.py`, `file.py` and
`inrange.py` have a card of their own. `Document.resolve` lays a node's params over `DEFAULTS`, so
a fallback where a param is read restates what the node already holds. A tool imports the player
inside `settings` alone, and its computing runs with no player.

Open: the form of a declaration. Recommended, and a session may build on it: plain values of the
language, as `DEFAULTS` is, that a tool writes with no import, so a tool's module still loads and
computes with no player.

- [ ] A tool declares each param in one place: its name, its default, its kind of row, and its
  range or its choices. The registry's table lists the facet with its hint.
  Check: `tests/test_registry.py`, the facet read from the table.
- [ ] A tool's defaults and its plain settings widget are made of that declaration by the player;
  no tool with a plain widget has a `settings` or a `DEFAULTS` of its own. A tool with a card of
  its own keeps its `settings`.
  Check: a one-off that builds every tool's widget offscreen at the commit before and at this one
  and compares, a tool at a time, the names in order, each row's kind, range and choices, and
  `params()`.
- [ ] No tool restates a default where it reads a param.
  Check: a grep for the fallbacks A11 names.
- [ ] Every document's plan prints what it printed, and loads to the params it loaded to.
  Check: the baseline, compared; a one-off over the documents for the params.
- [ ] What a tool raises for a param it refuses, and where, is as it was.
  Check: a one-off: every tool that refuses a choice, handed one it does not offer, raises the
  text it raised.

Worth a look: a tool's card in the player beside the same card on v5.

## What a wire carries is in one table

Assumes: The registry is the one reader of what a tool declares. Changes no key.

Facts to weigh. Part 4's H17: what lies on a `blobs` or a `tracks` wire is defined under `tools/`,
and the player knows it by its shape in `graph.py:nbytes`, `graph.py:gated` and `walk.py`.
`document.py:OVERLAYABLE` is a list of names. What a tool may import of the player is
`sieve_player.__all__`, held by `tests/test_seams.py`.

- [ ] One table under `sieve_player/`, named in `__all__` and importing no Qt, says of each type a
  wire carries its name, whether it is a table a row, how its bytes are counted and whether it can
  be overlaid. The player reads these of the table and of no result's shape; `tools/_table.py`
  reads the same table.
  Check: a grep for the shape tests H17 names; `tests/test_seams.py`, a seam, that a tool's
  `PRODUCES` and `EXPECTS` name types of the table.
- [ ] Every document's plan prints what it printed.
  Check: the baseline, compared.

## The display says which draws it paints

Assumes: The registry is the one reader of what a tool declares. Changes no key.

Facts to weigh. `Graph.watch` is told what the plot shows, and the worker folds for those and no
other. `Graph.drawing` takes the overlay's to be every fed frame node whose tool has a `draw`. The
document has a display flag and an overlay flag; the pins are the plot's and name signals.
Kendrick: "sometimes I want a draw on the video that is hard to surface as something needing it".

Open: which draw was hard to surface, and how one is named as wanted. Kendrick's to say here; a
session builds nothing on a guess of it.

- [ ] The display tells the graph the nodes whose `draw` it paints, as the plot tells it what it
  shows, and the worker computes at the row for those and no other.
  Check: a seam beside the test of `Graph.watch`: a fed frame node with a `draw` that the display
  does not name is not computed for the frame.

## A job goes by the keys it computes under

Assumes: nothing. Changes when a bare walk's results are kept.

Facts to weigh. A read, a walk and a cut are each ended when their own key moves
(`18c2010a`, `36e3565e`, `a603747b`). `window.py:PlayerWindow._bare_said` drops a bare walk's
results where the document is not, whole, the one the walk began under.

- [ ] A bare walk is ended, and its results dropped, when the key of a node it walks has moved and
  by no other change to the document.
  Check: a seam: a function of the keys the walk began under and the plan now answers whether it
  stands, and stands across a moved card, a node added off the chain and a param that is in no
  key.

## A csv names its footage by its print

Assumes: nothing. Changes a csv's key line.

Facts to weigh. `tools/_csvfile.py:key_line` names footage by a file's name, where the memo, the
held runs, a cut clip and a table of frame times name it by `decoder.footage_print`.

- [ ] A csv's key line names its footage by `decoder.footage_print`.
  Check: a one-off: a csv written of a clip and of a copy of it under another name carry one
  line.

## Held results and an edited tool

Assumes: nothing.

`held.py:stamp` holds a digest of every file in the tools' folder, and `held.py:File.load` answers
no runs under another, so an edit to any tool lets go of every document's held file. Kendrick: a
kept result does not go by a tool's code. Nuke's hash holds no plugin's code and a cache there is
cleared by hand; a plugin there changes at a release, and a tool here is edited most days. Without
the digest a result held before a tool was edited is served after it, looking as a fresh one
does, until it is let go by hand. The review rates a stale result served as the kind that matters
most.

- [ ] Kendrick: held results outlive an edit to a tool and are let go by hand, and that is wanted.

## A held file goes by the key alone

Assumes: Held results and an edited tool. Changes what is served after a tool is edited.

- [ ] The player lets go of a document's held results at a word from the user.
  Check: a seam: after it, `File.load` answers no runs.
- [ ] What a held file is good under holds nothing of the tools' code: an edited tool leaves a
  document's held runs serving.
  Check: a seam: a held file written, a tool's file touched, the runs read back.

## Keys that move once

Assumes: nothing.

A param out of a node's key moves the key of that node and of everything below it, once, and a
held file's runs under the old keys are found by nothing and walked again.
`docs/findings/2026-11-16-which-settings-no-run-reads.md` has which params those are as the tools
stand.

- [ ] Kendrick: said before it lands, and the held files of the documents in use may be walked
  again.

## A param that changes no result is in no key

Assumes: A param is declared once; Keys that move once. Changes keys.

Facts to weigh. `key_params` is Nuke's append: what a tool says of its key where a mark on a param
cannot, `region.py`'s rect, or a param read only under some value of another.

- [ ] A param's declaration says whether it changes what `run` hands out, and one left unsaid
  does.
  Check: `tests/test_registry.py`.
- [ ] A node's raw key holds its params that change the result, and what `key_params` answers for
  a tool that has one; a param declared to change nothing is in no key.
  Check: `tests/test_graph.py`, the seam of keys extended.
- [ ] For every param declared to change nothing, its tool's `run` hands out equal results of one
  input under two values of it.
  Check: a seam over every such param of every tool, so one `run` comes to read is found.

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
