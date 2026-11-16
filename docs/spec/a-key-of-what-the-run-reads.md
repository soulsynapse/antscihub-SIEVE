# A key of what the run reads: a param the run does not read is not in the node's key

Read with `sieve_player/plan.py`, whose `key_of` hashes a node's whole params into its key; with
`tools/region.py`, whose `run` reads a rect and whose params hold every shape, a quality and
`serve clip`; with `tools/_cutfile.py`, whose `rect_extent` already names a cut by what it holds;
and with the registry's facet table (`python -m sieve_player.registry`).

## How to read this

As `docs/spec/monitor.md`'s How to read this.

## Why

Five regions on one geometry file, a shape each, none served. A nudge to one shape is new params
for all five, since each holds every shape, so everything below all five is keyed anew and walked
again, though four hand out the pixels they did. `quality` and `serve clip` are in the key the same
way, and `run` reads neither. A served region has no such trouble: its key is its file's print, and
its file is named by its rect. The run is the one of the two still named by what was asked and not
by what is cut.

Nuke's op appends to its hash the knobs its output depends on and no others. What reads a cut next,
a tracker over every row, an identity, a table of periods, is where a walk again costs most, and
each tool that cuts by a shape, a period or an individual has params of the same kind: a table of
many, and a choice of one.

## A tool says what of its params its run reads

Assumes: nothing.

Facts to weigh. `served` raises with no shapes, where `run` raises too. A tool's `draw` and `pick`
read the node's params and never its key. A node's band is in its key and not its raw key, and is
the player's.

- [x] The registry's facet table lists a facet, `key_params(params)`, with its hint line: a JSON
  value that is the same for any two params under which `run` hands out the same result of the
  same input. A tool without it is keyed by its whole params, as now.
  Check: `tests/test_registry.py`, the facet read from the table with its hint.
- [x] A node's raw key is of its source's key, its tool and what the facet answers; where the facet
  raises, of its whole params.
  Check: `tests/test_graph.py`, a seam: under a tool with the facet, two params it answers alike
  have one key below them and two it answers apart have two.
- [x] region has the facet and answers the plate and the rect it cuts: a shape moved that is not
  the chosen one, a shape renamed, `quality` and `serve clip` leave every key below a region that
  runs as it was, and a chosen shape whose rect moved does not.
  Check: `tests/test_region.py`, a seam: the keys below a region across each of those changes,
  and, for every pair of those params the facet answers alike, `run` handing out equal arrays of
  one frame, so a param `run` comes to read and the facet does not is found.

## Not here

A node that hands on its input keyed as its source. With docs/spec/memo-holds-no-view.md such a
node costs a run's call a row and no plane, and what the plan would add is the keys below a rescale
at 1.0 being those with it out: a tool that hands on another row's frame, or its input at some rows
only, cannot say so from its params, and a region so keyed would not run, so its raise on a frame
that is not the plate's would not be made.

A document with a region has other keys below it than it had, so a held file's runs under the old
keys serve nothing and are walked again once.
