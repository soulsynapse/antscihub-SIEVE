# What a node declares, the key made of it, and everything going by that key

Read with `docs/systems-review.md`, E1 and E3 and the cut's line on C9; with `sieve_player/plan.py`,
which makes every key; with the registry's facet table (`python -m sieve_player.registry`); and with
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
| A node declares its knobs, once; the panel is made of them | A setting is declared once |
| The hash is the inputs' hashes and every knob but those flagged as not rerendering; a node may append to it | The key, of what is declared |
| The Viewer and the disk cache use the hash as their key directly | Every kept result, and every job, goes by the key |
| `_validate`: what the node hands out, said before a pixel is computed | What a wire carries, in one table |
| `_request`: the node is told what is wanted of it | What shows or writes a result says what it reads |

Nuke reads all of it off the Op and nowhere else, which here is the registry. A tool stays a module
of attributes: no class is inherited.

It is a large rework of small parts, so every deliverable but two changes no key and is held to the
plan printing what it printed. The two that change what is served or kept each carry a box that is
Kendrick's.

## The plans as they stand

Assumes: nothing.

What every later deliverable is compared with.

- [ ] `docs/findings/` holds what `python -m sieve_player <document> --plan` prints for each
  document under `video-tests/`, with the commit it was printed at.
  Check: the file is there, a table a document.

## The registry is the one reader of what a tool declares

Assumes: The plans as they stand.

Facts to weigh. Part 5's A2 lists the modules that read a tool's attributes themselves.
`document.py` imports nothing of the player, and its readers are there for that reason. `EXPECTS`
is a string or a tuple and is made a tuple in more than one place.

- [ ] No module under `sieve_player/` but the registry reads an attribute of a tool by `getattr`
  or `hasattr`; each asks the registry, by a name that says what is asked.
  Check: a grep, its pattern in the commit; `tests/test_seams.py`, a seam, that it stays so.
- [ ] What a tool expects is made a tuple in one place.
  Check: a grep.
- [ ] Every document's plan prints what it printed.
  Check: the baseline, compared.

## A setting is declared once

Assumes: The registry is the one reader of what a tool declares.

Facts to weigh. Part 5's A11: a setting's default, its row in `settings`, a check where it is
computed and a fallback where it is read. `ParamWidget.add_int`, `add_float`, `add_bool`,
`add_text`, `add_choice` and `add_list` are the kinds of row there are. `region.py`, `file.py` and
`inrange.py` have a card of their own. `Document.resolve` lays a node's params over `DEFAULTS`.

- [ ] A tool declares each setting in one place: its name, its default, its kind of row, its range
  or its choices, and whether it changes what `run` hands out. The registry's table lists the
  facet with its hint.
  Check: `tests/test_registry.py`, the facet read from the table.
- [ ] A tool's defaults, its plain settings widget and the refusal of a choice it does not offer
  are made of that declaration by the player; no tool with a plain widget has a `settings` or a
  `DEFAULTS` of its own. A tool with a card of its own keeps its `settings`.
  Check: a one-off that builds every tool's widget offscreen at the commit before and at this one
  and compares, a tool at a time, the names in order, each row's kind, range and choices, and
  `params()`.
- [ ] No tool restates a default where it reads a param.
  Check: a grep for the fallbacks A11 names.
- [ ] Every document's plan prints what it printed, and loads to the params it loaded to.
  Check: the baseline, compared; a one-off over the documents for the params.

Worth a look: a tool's card in the player beside the same card on v5.

## What a wire carries is in one table

Assumes: The registry is the one reader of what a tool declares.

Facts to weigh. Part 4's H17: what lies on a `blobs` or a `tracks` wire is defined under `tools/`,
and the player knows it by its shape in `graph.py:nbytes`, `graph.py:gated` and `walk.py`.
`document.py:OVERLAYABLE` is a list of names.

- [ ] One table under `sieve_player/` says of each type a wire carries its name, whether it is a
  table a row, how its bytes are counted and whether it can be overlaid. The player reads these of
  the table and of no result's shape; `tools/_table.py` reads the same table.
  Check: a grep for the shape tests H17 names; `tests/test_seams.py`, a seam, that a tool's
  `PRODUCES` and `EXPECTS` name types of the table.
- [ ] Every document's plan prints what it printed.
  Check: the baseline, compared.

## The display says which draws it paints

Assumes: The registry is the one reader of what a tool declares.

Facts to weigh. `Graph.watch` is told what the plot shows, and the worker folds for those and no
other. `Graph.drawing` takes the overlay's to be every fed frame node whose tool has a `draw`.
Kendrick: "sometimes I want a draw on the video that is hard to surface as something needing it".

- [ ] The display tells the graph the nodes whose `draw` it paints, as the plot tells it what it
  shows, and the worker computes at the row for those and no other.
  Check: a seam beside the test of `Graph.watch`: a fed frame node with a `draw` that the display
  does not name is not computed for the frame.

Open: how a draw is named as wanted in the player, a flag on a node's card or the pins. The
session builds on the pins unless this line is edited.

## A job goes by the keys it computes under

Assumes: nothing.

Facts to weigh. A read, a walk and a cut are each ended when their own key moves
(`18c2010a`, `36e3565e`, `a603747b`). `window.py:PlayerWindow._bare_said` drops a bare walk's
results where the document is not, whole, the one the walk began under.

- [ ] A bare walk is ended, and its results dropped, when the key of a node it walks has moved and
  by no other change to the document.
  Check: a seam: a function of the keys the walk began under and the plan now answers whether it
  stands, and stands across a moved card, a node added off the chain and a setting that changes no
  result.

## Every kept result goes by the key

Assumes: nothing.

Facts to weigh. The finding's table of the six places. A cut clip and a table of frame times are
of footage and are named by its print; neither is a node's result. `held.py:stamp` holds a digest
of every file in the tools' folder, and `held.py:File.load` answers no runs under another.
Kendrick: a kept result does not go by a tool's code. Nuke's hash holds no plugin's code, and a
cache there is cleared by hand.

- [ ] A csv's key line names its footage by `decoder.footage_print`.
  Check: a one-off: a csv written of a clip and of a copy of it under another name carry one
  line.
- [ ] The player lets go of a document's held results at a word from the user.
  Check: a seam: after it, `File.load` answers no runs.
- [ ] What a held file is good under holds nothing of the tools' code: an edited tool leaves a
  document's held runs serving.
  Check: a seam: a held file written, a tool's file touched, the runs read back.
- [ ] Kendrick: results held before a tool was edited are served after it until they are let go
  by hand, and that is wanted.

## A setting that changes no result is in no key

Assumes: A setting is declared once.

Facts to weigh. The finding has which settings no computing facet reads as the tools stand.
`key_params` is Nuke's append: what a tool says of its key where a flag on a setting cannot,
`region.py`'s rect.

- [ ] A node's raw key holds its settings that are declared to change the result, and what
  `key_params` answers for a tool that has one; a setting declared to change nothing is in no key.
  Check: `tests/test_graph.py`, the seam of keys extended.
- [ ] For every setting declared to change nothing, its tool's `run` hands out equal results of
  one input under two values of it.
  Check: a seam over every such setting of every tool, so one `run` comes to read is found.
- [ ] Kendrick: every key below a node with such a setting moves once, and a held file's runs
  under the old keys are walked again; said before it lands.

## What is asked for is one set the worker reads

Assumes: The display says which draws it paints.

Facts to weigh. `worker.py:Worker._turn` is a ladder of four rungs, and what each makes is read
of `Plan.walk`, `Graph.drawing` and `Graph.watch`. A walk with no window, which
`docs/spec/pieces-of-footage.md` adds, is a reader with no rung. Not sized: `worker.py` and the
three methods of `graph.py` were not read for it.

- [ ] Each thing that shows or writes a result says what it reads as a value: who asks, which
  node, which rows, and whether its result, its fold or its drawing. The worker computes what the
  asks name and nothing else.
  Check: a seam: with no ask naming a node, no run of it is in the stream.

Fork: whether the ladder's order survives as a rank on an ask or is replaced. Observed once the
display's and the plot's asks are values: what `_turn` still decides that no ask says, written in
the commit.

## Not here

A tool's code in a key. A class a tool inherits. A surface held still across versions. Whether a
stepped node's result is a function of its key, which is `docs/spec/pieces-of-footage.md`'s first
box. One place a failure is said, the review's E4. The window's memory of a path loader's file,
which keeps no result.
