# SIEVE — Signal Isolation of Ethological Video Events

SIEVE runs independent video-analysis scripts as nodes in one graph, under one shared player, so no
script needs a GUI of its own. A script is a **tool**; `sieve_player` is the player; a pipeline is a
**document** of nodes and wires saved as JSON. The player knows no tool by name: everything it does
with a tool, it learns from the attributes the tool declares.

```
py -3.13 -m venv .venv            # not the Anaconda python: its Qt DLLs shadow PySide6's
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py [video]                     # the example pipeline, every tool under tools/ placeable
.venv\Scripts\python -m sieve_player doc.json [root ...] # a saved document, against the tools under the roots
.venv\Scripts\python -m sieve_player doc.json --plan      # the plan instead: each node's kind, key, role and standing
.venv\Scripts\python tools\motion.py [video]             # any tool runs alone
.venv\Scripts\python smoke.py video                      # offscreen end-to-end check
.venv\Scripts\python -m pytest
.venv\Scripts\python -m sieve_player.registry --check    # the tools, their facets, the types they use
```

What the player prints to stderr, tracebacks, Qt warnings, the watchdog's and a crash's stacks, it
also writes to a log, the previous launch's kept beside it as `.prev.log`; `SIEVE_LOG` names the
file or, as `0`, turns it off, and `sieve_player.dev.console.log_path` says where it goes unset. `SIEVE_DUMP`
names a file every video opened dumps the probe's stream to (`sieve_player/trace.py`);
`SIEVE_QT_TRACE` narrows the Qt warning handler to warnings containing its text, or `0` leaves
Qt's own printing alone; `SIEVE_C_STDERR=1` leaves C-level stderr alone, so cv2's plugin warns on
every unconverted frame, and libav says why a stream ended where it did, which the player's own
line at the correction cannot. `SIEVE_MEMO_GB` and `SIEVE_CACHE_GB` set the memo's and the
decoder cache's limits; unset or `0`, each is the default in its class, and the line the player prints on
opening a video says what both are. `SIEVE_STORE` names the store, the folder bakes land in, while
no folder has been chosen in the player; `sieve_player.store.folder` says where it is otherwise.

## A tool

A tool is one Python file with `SIEVE_TOOL = True` and a `NAME`. Everything else is a facet it may
or may not declare; `sieve_player/registry/README.md` says how tools are found and what a missing
facet means, and `python -m sieve_player.registry` lists the facets the player reads.

A tool does one thing, and a wanted variation is a second tool wired beside it, never a knob on
the first: applying one node's output to another's is a node of its own that reads both, not a
setting hidden on either. Chains get longer; tools do not get wider.

```python
# a frame tool: one row in, one array out
NAME = "threshold"; KIND = "frame"; EXPECTS = "gray"; PRODUCES = "mask"
DEFAULTS = {...}                              # JSON-able
def run(frames, row, params) -> np.ndarray    # frames(r) is the output of the node it reads, at row r
def settings(parent=None) -> ParamWidget

# a series tool: the whole loop window at once
NAME = "reduce"; KIND = "series"; EXPECTS = ("gray", "mask"); PRODUCES = "signal"
def fold(frame) -> np.ndarray                 # optional: what the walk stacks per row in place of the
                                              # frame, so the window holds (T, small) and never the planes
def run(series, params) -> dict               # series.data is (T, ...), the read node stacked, each row
                                              # through fold() if there is one; the dict carries "signal",
                                              # a (T,) array; the gate is the player's, never the tool's
def settings(parent=None) -> ParamWidget      # optionally show_result(result, start, fps), set_playhead(row),
                                              # set_source(path, fps): the video, for a tool that writes a file (csv)
def step(state, row, i, params) -> (state, dict)  # optional: the tool steps row by row where the plan lets it,
                                              # state None at the first row; equal to run over the same rows (travel)

# a series tool reading another: EXPECTS = "signal", and series.data is the upstream result's
# "signal" with the rows its band shuts out zeroed (smooth); or, when the upstream result also
# carries "rows", one table a row (track), those tables, emptied where the band shuts them out (travel).

# a frame tool with more inputs: INPUTS = {"diff": "gray"}, read as frames(row, "diff"); one named
# in OPTIONAL = ("diff",) may be unwired and then reads as None (blobs). frames.type(input) is what
# the node wired into an input produces, for an EXPECTS whose types run() must tell apart (inrange).

# a tool on a wire of any kind: KIND = "same" makes the node a frame node on a frame wire and a
# series node on a signal or tracks wire, so run is called either way, run(frames, row, params) or
# run(series, params), and settles which by its arguments (bake).

# a selector: which file, by rule
NAME = "file"; KIND = "selector"; PRODUCES = "path"
def select(folder, params) -> str | None      # folder is the document's
```

How the player treats a tool, as `sieve_player/graph.py`, `pane.py` and `window.py` do:

- Types are strings the player compares for equality; it attaches no meaning to them beyond the
  video node producing `"bgr"`, or `"gray"` when its `output` param says so. That one param is the
  decoder's, applied before its cache, so a chain that wants gray frames never holds the colour
  ones and no gray node is needed for that; a smaller frame is tools/rescale's, or a bake's, and a
  document saved with a scale on the video node loads with a rescale node inserted for it. An
  `EXPECTS` tuple accepts any of its members, and `PRODUCES = "same"` hands out whatever the tool
  reads.
- Only the worker thread calls `run`, but for any row in any order, since a seek jumps its queue.
  `frames.key` / `series.key` changes whenever anything upstream does; the tools that cache key on
  it and on their own params. A `frames()` read made after the node's key has changed under the
  run, or while the player is closing, raises `graph.Cancelled` and the row is dropped: a run of
  many reads ends at its next one, so a tool never needs to poll for interruption and must not
  swallow that exception. A read past the last row the stream has raises `decoder.EndOfStream`,
  the one IndexError the worker closes a walk on; a tool reading rows the container claims
  (background) catches it by that name, and any other IndexError is the tool's failure.
- The tools under `tools/` import Qt, and the parts of `sieve_player` that import it, inside
  `settings()`, `draw()` and their `__main__` block rather than at module top, which lets a script
  without Qt import them and call `run`; a player module that imports no Qt, `document` or
  `decoder`, may be imported at top (background imports the decoder's `EndOfStream`).
- The document holds the params. The pane moves a settings widget's knobs to them with
  `set_params()` and writes `params()` back on every change; `ParamWidget` provides both, and a
  widget without them is shown as a defect.
- Each node reads one node through its first input, `"in"`, the one a drop onto a wire lands on and
  a `"same"` output follows. A frame tool may declare more in `INPUTS`, each a wire of its own, and
  `run` reads one as `frames(row, name)`. A node the video does not reach through every frame
  input, over wires whose types fit, computes as None, and so does everything downstream of it.
  Why a node does not run is its standing, one line the runtime states per node (`Graph.standing`):
  the pane shows it under the node's settings, the canvas as its tooltip, and `--plan` prints it. A
  tool raising, or a chain node handed no signal, is noted there too, until the node's key changes.
- Series nodes run as a chain: the walked node is what the first series node reading a frame node
  reads, every series node reading that node is a head and runs on the stacked window, and each
  fed series node wired on from a chain node runs after it on the upstream result's `"signal"`. A
  series node reading another frame node does not run.
- A series tool's `fold(frame)` runs on the worker as each row is computed and takes no params: a
  change to the tool's params reruns `run` on the stack already folded, so a fold must hold every
  number any params could ask for (reduce folds a row to its sum, max, count and size). The walk
  folds only when every head folds the same way; otherwise it stacks the rows as they are and each
  head with a fold folds them at run, and the clip walk refuses a stack of frames.

Facets the player reads when a tool has them:

| facet | what the player does with it |
|---|---|
| `draw(painter, row, result, start, params)` | paints on the frame, in frame-pixel coordinates (`painter.window()` is the frame's rect), with the node's params as they stand; one that raises is dropped for the session |
| `pick(point, shape, row, result, params)` | a drawer answers a left click on the frame: `point` is (x, y) in the displayed frame's pixels and `shape` that frame's (height, width); it returns the params to merge into the node, landed as a card's change is, or None for a click it does not claim. The drawers are asked last-drawn first and the first answer wins; one that raises is dropped for the session, as a draw is, through every change of the graph. A right click moves the display flag back to the node shown before |
| a `"signal"` array in a series result | the node's trace, drawn as a detector. Its two handles are the node's band, in the signal's units, saved with the node: the player adds `"gate"`, the rows inside it (outside when lo is above hi), washes them on the trace, zeroes the rest of the signal before a series node downstream reads it, and draws a green border on the frame while the playhead is in a row the last chain node gates. Every chain node's result also gets `"key"`, the node's key (`graph`), which hashes its band and everything upstream: a tool that writes a file records it, and can read it back to say whether the file on disk is this graph's (csv) |
| `INPUTS = {input: types}` | a frame input after the first, with the types it expects; `run` reads it as `frames(row, input)`, and the node's key and `frames.key` follow it |
| `PATHS = {input: loader}` | a path input a selector feeds; the loader turns the file into params |
| `def bake(params, count) -> (rows, quality)` | the node bakes: a Bake button under it, and the worker writes the node's input over the plate rows the tool reads off its own params into the store (`sieve_player/store.py`) under the node's key, a row at a time between scrubs, frame kinds as a clip at the quality the tool names and tables and signals as files that read back equal (`sieve_player/writers.py`); a cancelled or failed bake leaves nothing and says why in the node's standing. The node's mode, live or baked, is the document's, saved with the node and drawn on it; baked, the node is a source: fed with nothing wired in, keyed by its bake, handing out the file's kind with nothing upstream run or decoded; a change upstream shows it stale, the plan's verdict and never saved, and the switch under it goes live or serves the bake again, and a document reopens baked while the store has the file. While the display flag is behind a bake with an increment or a range, the document's rows, count and fps are the file's, nodes in the plate's row space are grayed and do not run, and a csv's key line carries `plate=first:increment`; with the flag upstream of every bake the document is the plate's and the nodes behind the bake are the grayed ones |
| `STATIC = True` | the output is the same at every row: the memo holds it once under the key and never evicts it while the node stands under that key, and the monitor counts its run per change rather than per row |
| a plane as output | the node's density, v2's plot: its pixels per row counted on a fixed log axis, under its settings, for every fed frame node; a mask or a field has none. Its two handles are the node's band, saved with the node: the player zeroes every pixel outside it (inside it when lo is above hi) before anything downstream reads the node |

`tools/` holds a working example of each. A module there whose name begins with `_` is not a tool
but what tools share, the table kind in `_table.py` and its drawing in `_draw.py`; a tool imports
from those and from no other tool, which `tests/test_seams.py` checks.

## The player

The frame is on the left, the node canvas over the selected node's parameters on the right, and
the timeline across the bottom. The node with the display flag is what the frame shows; the node
with the overlay flag, a second disc offered only on a node producing one plane (`document.OVERLAYABLE`),
is heated over it, cold-to-hot in v2's ramp, and a click on the flag it carries turns it off; selection
only chooses what the pane shows. A worker thread computes and the GUI thread
reads: every node's output is memoized under a key built from its params and its
upstream, and the display shows what the memo holds.

Each module's docstring says what it does: `document` (the saved form; imports no Qt or cv2),
`graph` (the runtime), `worker`, `canvas`, `pane`, `window`, `timeline`, `theme` (the design
language). `tests/test_seams.py` checks which imports which.

This file describes the code; where the two disagree, the code is what SIEVE does.