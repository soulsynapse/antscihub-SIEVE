# Pass-through: a node that hands on its input unchanged is its source in the plan

Read with docs/spec/memo-holds-no-view.md, which this builds on and whose finding says what a
passing node costs while it still runs; with `sieve_player/plan.py`, whose `key_of` is where a
served node already takes another node's key; with `sieve_player/graph.py`, whose `_compute`
memoizes and whose `peek` the window paints from; with `sieve_player/catalogue.py` and
`sieve_player/ledger.py`, which read a node off a key; and with the registry's facet table
(`python -m sieve_player.registry`).

## How to read this

As `docs/spec/monitor.md`'s How to read this. No box here is available until
docs/spec/memo-holds-no-view.md is ticked whole and both items under Open are settled in this file.

Words. A node *passes* when, at the params it has, what it hands out at every row is what its first
input handed it, pixel for pixel and shape for shape. A node *makes* under a key when its tool's run,
or a decoder's read, is what computes the result held under it.

## Why

With the memo holding no view, a node that passes is run and its result held as a copy: a plane a
row of the memo and a copy's time for a result the store above it already has. A node that passes
has a key of its own, so everything below it is keyed anew when it starts or stops passing, a
rescale dragged to 1.0 and back, a shape chosen and cleared, though the pixels are the same.

Nuke leaves a disabled node, or one that is a no-op at its knobs, out of the op tree, so the hashes
below it are what they would be without it; a bypassed Houdini SOP hands on its input's detail
handle; a muted Blender node routes through its internal links. Each settles identity before
evaluation. The plan already does this for a served clip.

## A tool says when it passes

Assumes: nothing.

Facts to weigh. region's `DEFAULTS` has no shapes, and with none `served` raises, so a check that
runs a tool at its defaults never sees region pass.

- [ ] The registry's facet table lists a facet, with its hint line, by which a frame tool answers
  from its params alone whether it passes.
  Check: a test reads the facet from the table and the hint.
- [ ] Each tool that has the facet, at params under which it answers yes, hands out a result equal
  to the frame it read; at params under which it answers no, the facet is the only thing that
  changed. The tools that have it are those the ruling under Open leaves, rescale at a scale of 1.0
  among them.
  Check: `tests/test_tools.py` or the file that holds the tools' seams: each tool with the facet is
  run at params built to pass, region's with shapes and no choice if region has it.

## A passing node is its source in the plan

Assumes: A tool says when it passes.

Facts to weigh. `plan()` is pure and sees no decoder, so it knows no frame's shape. A node's band is
applied on read and is in its key, not its raw key. `Graph.peek` reads the memo or a cache by the
entry's kind, and the window paints the shown node from it. Until now one node makes under one key:
`catalogue.store_name` and the catalogue's naming of a store's node each read the node off a walk's
`keys`, and the memo's evictions reach the stream by key alone.

- [ ] A fed frame node that passes, and serves no file, has its source's raw key, and its key is
  that with its own band; every node below it is keyed as it would be were it wired to that source.
  A node that stops passing, and passes again, has the keys it had.
  Check: `tests/test_plan.py`, a seam: the keys below a rescale at 1.0 are those with it out, and
  those of a rescale moved to 0.5 and back.
- [ ] A passing node's result at a row is its source's, banded by its own band: its tool is not run,
  the memo holds nothing under it, and `peek` answers for it whatever it answers for its source.
  Check: a one-off under `docs/findings/experiments/` walks a plan with a passing node shown and
  reads its frame painted with no span on the node.
- [ ] Wherever the catalogue, the ledger or the report reads a node off a key, the node is the one
  that makes under it and never one that passes; the plan's facts say which nodes pass and what
  each passes.
  Check: `tests/test_catalogue.py`, a seam: a walk with a passing node between the video and a
  frame tool names the video's cache and attributes a discarded result by the nodes that made them.

## The monitor says what passes

Assumes: A passing node is its source in the plan.

- [ ] The report's table has a row for a passing node that says it passes and which node it is; it
  has no ms.
  Check: the one-off reads the report.
- [ ] On the plan of docs/spec/memo-holds-no-view.md's finding, the figures that finding holds are
  read again beside it.
  Check: the one-off, its figures in the same finding or one beside it.

## Not here

A tool that passes at some rows and not others. A second input passed. A series or stepping tool
that passes.

A document with a passing node has other keys below it than it had, so a held file's runs under the
old keys serve nothing and are walked again once.

## Open

- Whether region has the facet. A region that passes is not run, so its raise on a frame that is
  not the plate's shape is not made: a region with none chosen, wired after a rescale, hands the
  frame on and says nothing until a shape is chosen. `tools/region.py`'s docstring and
  docs/spec/region.md say it raises, and the plan knows no shape to say it by. Without region the
  facet has one tool, rescale, at a value that is not its default. Kendrick's.
- Whether the finding of docs/spec/memo-holds-no-view.md makes this worth a facet at all, and the
  facet's name. Kendrick's.
