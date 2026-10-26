# The graph and its runtime

The runtime computes what the graph says. It takes a document and a decoder and answers, for a
node and a row, what that node's output is, memoized under a key that changes whenever anything
upstream changes. The module to read before touching this is `sieve_player/chain.py`: its memo,
keys, `Frames` and `Series` are the parts that survive; `Links`, which assumed a list, does not.

## Graph runtime

Assumes: Document module.

- [ ] The runtime is built from a document and a decoder, not from a list of tools.
  Check: a test builds one from a document with a fan-out wire.
- [ ] A node reads the node its input wire names; the video node is a node like any other and
  produces `"bgr"`.
  Check: a test computes a node whose input is the video node.
- [ ] Two nodes may read the same node (fan-out), and each gets the same memoized output.
  Check: a test with two readers asserts one computation.
- [ ] A node with no wire into its input computes as None, and so does every node downstream of
  it.
  Check: a test in `tests/`.
- [ ] A node's memo key changes when its params change, when any upstream node's params change,
  and when its input is rewired; it does not change when a node it does not read changes.
  Check: a test for each.
- [ ] Rewiring or re-parameterizing the graph while a worker is computing does not crash and
  the next computation reflects the new graph.
  Check: a test rewires from the main thread during a worker walk.
- [ ] A series node is computed over the loop window from the node it reads, as today, and at most
  one series node is active; a document with more than one is accepted and the runtime reports
  which one it will not run.
  Check: a test loads a two-series document and reads the report.
- [ ] Tool `run`, `EXPECTS`, `PRODUCES`, `DEFAULTS`, `settings`, `draw` and the export facets keep
  the meaning the registry's README gives them; a dummy written to that contract runs in the
  graph without knowing it is in one.
  Check: the dummies run in a graph built from a list, in `smoke.py`.

## Dummy tools

Assumes: nothing.

- [ ] A root the registry discovers holds tools whose `run` returns its input, zeros of the right
  shape, or a constant series, covering: a `"bgr"` to `"gray"` tool, a `"gray"` to `"gray"` tool,
  a pass-through, a tool expecting a tuple of types, a series tool, and a tool that exports.
  Each has a settings widget with at least one control.
  Check: `python -m sieve_player.registry <root>` lists them with no facet unsaid.
- [ ] The dummies are what canvas and window deliverables are developed against; nothing in
  `sieve_player` names one.
  Check: a grep of `sieve_player/` for the dummy root finds nothing.

## Non-goals

- Fan-in: a node with more than one input. Every tool today reads one stage, and a second input
  changes `run`'s signature for every tool. It is the first thing to revisit after the canvas
  feels right, and the document already stores the destination's input name so it costs nothing
  to admit later.
- Params as connectors (Blender style). Params stay on the pane; a param is never wired.
- More than one running series node. One worker, one stack. The document admits it so the
  runtime can grow into it.
- Bypass. `PRODUCES = "same"` tools already pass through; a general bypass flag waits until a
  tool needs it.
