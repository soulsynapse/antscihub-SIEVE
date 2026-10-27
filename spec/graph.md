# The graph and its runtime

The runtime computes what the graph says. It takes a document and a decoder and answers, for a
node and a row, what that node's output is, memoized under a key that changes whenever anything
upstream changes. The module to read before touching this is `sieve_player/graph.py`; its memo,
keys, `Frames` and `Series` carried over from the list-shaped runtime it replaced.

## Graph runtime

Assumes: Document module.

- [x] The runtime is built from a document and a decoder, not from a list of tools.
  Check: a test builds one from a document with a fan-out wire.
- [x] A node reads the node its input wire names; the video node is a node like any other and
  produces `"bgr"`.
  Check: a test computes a node whose input is the video node.
- [x] Two nodes may read the same node (fan-out), and each gets the same memoized output.
  Check: a test with two readers asserts one computation.
- [x] A node with no wire into its input computes as None, and so does every node downstream of
  it.
  Check: a test in `tests/`.
- [x] A node's memo key changes when its params change, when any upstream node's params change,
  and when its input is rewired; it does not change when a node it does not read changes.
  Check: a test for each.
- [x] Rewiring or re-parameterizing the graph while a worker is computing does not crash and
  the next computation reflects the new graph.
  Check: a test rewires from the main thread during a worker walk.
- [x] A series node is computed over the loop window from the node it reads, as today, and at most
  one series node is active; a document with more than one is accepted and the runtime reports
  which one it will not run.
  Check: a test loads a two-series document and reads the report.
- [x] Tool `run`, `EXPECTS`, `PRODUCES`, `DEFAULTS`, `settings`, `draw` and the export facets keep
  the meaning the registry's README gives them; a dummy written to that contract runs in the
  graph without knowing it is in one.
  Check: the dummies run in a graph built from a list, in `smoke.py`.

## Dummy tools

Assumes: nothing.

Retired on 2026-10-26: Kendrick removed the dummies once the graph ran the real tools, so the
boxes below describe a root that no longer exists. Nothing assumes them that is not already met by
`tools/`; `smoke.py` runs the real chain, and the selector of the next deliverable is `tools/file.py`.

- [x] A root the registry discovers holds tools whose `run` returns its input, zeros of the right
  shape, or a constant series, covering: a `"bgr"` to `"gray"` tool, a `"gray"` to `"gray"` tool,
  a pass-through, a tool expecting a tuple of types, a series tool, and a tool that exports.
  Each has a settings widget with at least one control.
  Check: `python -m sieve_player.registry <root>` lists them, and every facet in `FACETS` is said
  by at least one of them.
- [x] The dummies are what canvas and window deliverables are developed against; nothing in
  `sieve_player` names one.
  Check: a grep of `sieve_player/` for the dummy root finds nothing.

## Selector nodes

Assumes: Graph runtime, Dummy tools.

A selector is a tool that answers which video file a document means, from a rule rather than a
written path: the newest `.mp4` beside the document, any `.avi` under a subfolder, and so on. It
is a node like any other so the rule is visible on the canvas and can be swapped for a different
selector; it feeds the video node, which is the one node that reads a path and not a frame.

- [x] A tool whose `PRODUCES` is `"path"` and that expects nothing is a selector. It defines
  `select(folder, params)`, which answers a path or None from the document's folder and its
  params, and it is asked when the document opens and whenever its params or its wire change,
  never per row. `select` is a facet the registry's README lists.
  Check: a test builds a document with a selector wired to the video node and reads which path
  the document means; `python -m sieve_player.registry --check` passes.
- [x] The video node has one input, expecting `"path"`. With nothing wired to it, the document's
  `video` names the file, as today. With a selector wired to it, the selector's answer names the
  file and is written into `video` as written, relative to the document's folder, so a reader
  without the selector's tool still opens the same file.
  Check: a test saves a document whose selector matches a file beside it and reads `video` back.
- [x] Validation does not report the video node's input as unfed, and a selector node is neither
  unfed nor reachable from the video: it is upstream of everything and reads nothing.
  Check: a test validates a document with and without a selector and asserts no report on either.
- [x] A `"path"` output fits only an input that expects `"path"`; a wire from a selector into a
  frame tool is a type problem like any other mismatch.
  Check: a test validates such a wire.
- [x] The runtime computes a selector node as None at every row, and the video node's memo key
  changes when the file the document means changes.
  Check: a test rewires the selector and compares the video node's key before and after.
- [x] A selector that answers None, or a path that will not open, is reported on the video node
  exactly as a written path that will not open is, and leaves what was open alone.
  Check: a test asks a selector whose rule matches nothing and reads the report.
- [x] A dummy selector picks by a folder relative to the document, a glob, whether to recurse, and
  an order (by name or by newest), taking the first match. Its settings widget has a control for
  each.
  Check: a test resolves it against a temporary tree; the registry lists it.

## Path inputs

Assumes: Selector nodes.

A tool that reads a file beside its frames, as inrange reads a colour settings JSON, can take
that file from a selector instead of a dialog, so a saved pipeline finds its own settings the
way it finds its own video.

- [x] A tool may declare `PATHS`, path-input name to a loader; each is an input of type `"path"`
  beside its frame input, and `run` never sees it. A selector wired into one answers the file;
  the loader turns the file into params, which land on the node once per picked file, so the
  knobs show what the file said and the memo key follows.
  Check: a test wires a selector into inrange's `settings` and reads the node's params.
- [x] Validation treats a path input like the video node's: a `"path"` output fits it, nothing
  else does, and an empty one is not unfed.
  Check: a test validates a frame output wired into a path input and an empty path input.
- [x] A selector that answers nothing, or a file the loader rejects, is said on that node in red
  and under its settings, and the params it had stay.
  Check: a test picks a settings file that is not one and reads the report.

## Non-goals

- Fan-in: a node with more than one input. Every tool today reads one stage, and a second input
  changes `run`'s signature for every tool. It is the first thing to revisit after the canvas
  feels right, and the document already stores the destination's input name so it costs nothing
  to admit later. Lifted on 2026-10-26 for path inputs alone, under Path inputs above: they
  never reach `run`, so the reason does not apply to them.
- Params as connectors (Blender style). Params stay on the pane; a param is never wired.
  Lifted on 2026-10-26 for the video node's source alone, under Selector nodes above. The fence
  kept the build-out off side quests; it was never a verdict on the finished graph, and the same
  is true of the rest of this list.
- More than one running series node. One worker, one stack. The document admits it so the
  runtime can grow into it.
- Bypass. `PRODUCES = "same"` tools already pass through; a general bypass flag waits until a
  tool needs it.
