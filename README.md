# SIEVE: Signal Isolation of Ethological Video Events

SIEVE runs independent video-analysis scripts as nodes in one graph, under one shared player, so no
script needs a GUI of its own. A script is a **tool**; `sieve_player` is the player; a pipeline is a
**document** of nodes and wires saved as JSON. The player knows no tool by name: everything it does
with a tool, it learns from the attributes the tool declares.

```
py -3.13 -m venv .venv            # not the Anaconda python: its Qt DLLs shadow PySide6's
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py                             # the document last opened or saved, every tool under tools/ placeable
.venv\Scripts\python main.py video                       # the example pipeline on a video; also what opens when no document is noted
.venv\Scripts\python -m sieve_player [doc.json [root ...]] # a saved document, against the tools under the roots; none named: the last
.venv\Scripts\python -m sieve_player --plan               # the last document's plan, with none named
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
Qt's own printing alone; `SIEVE_C_STDERR=1` leaves C-level stderr alone, so libav says
why a stream ended where it did, which the player's own
line at the correction cannot. `SIEVE_MEMO_GB` and `SIEVE_CACHE_GB` set the memo's and the
decoder cache's limits; unset or `0`, each is the default in its class, and the line the player prints on
opening a video says what both are.

## A tool

A tool is one Python file with `SIEVE_TOOL = True` and a `NAME`. Everything else is a facet it may
or may not declare; `sieve_player/registry/README.md` says how tools are found and what a missing
facet means, and `python -m sieve_player.registry` lists the facets the player reads.

The same facets answer questions about the catalogue as a whole; docs/findings/2026-11-09-tool-report-canaries.md
has two reports derived from them, what each found and what it could not see.

A tool does one thing, and a wanted variation is a second tool wired beside it, never a knob on
the first: applying one node's output to another's is a node of its own that reads both, not a
setting hidden on either. Chains get longer; tools do not get wider.

```python
# a frame tool: one row in, one array out
NAME = "threshold"; KIND = "frame"; EXPECTS = "gray"; PRODUCES = "mask"
PARAMS = {"thresh": {"default": 128, "kind": "int", "range": (0, 255)}}   # every param, once, JSON-able: the player
                                              # makes a node's first params and its card of it
def run(frames, row, params) -> np.ndarray    # frames(r) is the output of the node it reads, at row r, read-only

# a series tool: the whole loop window at once
NAME = "reduce"; KIND = "series"; EXPECTS = ("gray", "mask"); PRODUCES = "signal"
def fold(frame) -> np.ndarray                 # optional: what the walk stacks per row in place of the
                                              # frame, so the window holds (T, small) and never the planes
def run(series, params) -> dict               # series.data is (T, ...), the read node stacked, each row
                                              # through fold() if there is one; the dict carries "signal",
                                              # a (T,) array; the gate is the player's, never the tool's
def settings(parent=None) -> ParamWidget      # optional, a card of the tool's own in place of the one made of PARAMS,
                                              # which may have show_result(result, start, fps), set_playhead(row),
                                              # set_source(path, fps): the footage the node's inputs are frames of, the video or
                                              # the file a cutting node above it serves, for a tool that writes a file (csv),
                                              # set_paths({input: path}): the file each wired path input picked,
                                              # for a card that opens the file in another program
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
# run(series, params), and settles which by its arguments.

# a selector: which file, by rule
NAME = "file"; KIND = "selector"; PRODUCES = "path"
def select(folder, params) -> str | None      # folder is the document's
```

How the player treats a tool, as `sieve_player/graph.py`, `pane.py` and `window.py` do:

- Types are strings the player compares for equality, each a row of `sieve_player/wire.py`'s
  table, which says whether a row of it is a table, how its bytes are counted and whether it can
  be overlaid; a new type is added there first, which `tests/test_seams.py` checks. The video node
  produces `"bgr"`, or `"gray"` when its `output` param says so. That one param is the
  decoder's, applied before its cache, so a chain that wants gray frames never holds the colour
  ones and no gray node is needed for that; a smaller frame is tools/rescale's, and a
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
| `pick(point, shape, row, result, params)` | a drawer answers a left click on the frame: `point` is (x, y) in the displayed frame's pixels and `shape` that frame's (height, width); it returns the params to merge into the node, landed as a card's change is, or None for a click it does not claim. The drawers are asked last-drawn first and the first answer wins; one that raises is dropped for the session, as a draw is, through every change of the graph. |
| a `"signal"` array in a series result | the node's line in the plot under the frame, drawn while the node is selected or pinned. Its two handles are the node's band, in the signal's units, saved with the node: the player adds `"gate"`, the rows inside it (outside when lo is above hi), washes them on the line, zeroes the rest of the signal before a series node downstream reads it, and draws a green border on the frame while the playhead is in a row the last chain node gates. Every chain node's result also gets `"key"`, the node's key (`graph`), which hashes its band and everything upstream: a tool that writes a file records it, and can read it back to say whether the file on disk is this graph's (csv) |
| `INPUTS = {input: types}` | a frame input after the first, with the types it expects; `run` reads it as `frames(row, input)`, and the node's key and `frames.key` follow it |
| `PATHS = {input: loader}` | a path input a selector feeds; the loader turns the file into params |
| `def cut_file(video, footage, params) -> path or None` | the node cuts the video into files: at every sync the player asks which file the tool wrote of what `run` hands out of `video`, whose `decoder.footage_print` is `footage`, under the node's params; the file may be a lossy encoding of it, and what is served is the file. While the node reads the video node, or a node that serves a file, in which case `video` is that file, the player serves the file in place of the run: nothing upstream is run or decoded for it, its key is the one a document opened on the file gives its video node, so everything after it is keyed as that document is, and its face on the canvas says `cut`. With None for an answer, or a node that serves none between the video and it, it runs. A tool whose params say to serve a file that is not there raises FileNotFoundError saying why: the node and everything that reads it then do not run, and what it said is the node's standing, so a document's results never depend on what the store holds. A file a node serves is open in the player, and in a bare walk's process, and cannot be replaced or removed while it is, so a tool never writes over a file it has answered with: a cut of another part, or another encoding, is a file of another name in the store, the folder the header's store control shows and a press on it chooses (`tools/_cutfile.py`, `sieve_player/store.py`), and a settings widget that has written or removed one says so by a `storeChanged` signal, its params as they were, for the player to read the store and ask again. A tool whose `cut_file` or `cut_files` raises serves and names nothing, and its node's standing says what was raised. The served files' decoders share one cache limit, the video decoder's: the file read latest may fill the whole of it, and the others keep what is left, the one read longest ago giving way first. A node reads one piece of the plate: one whose inputs are of two cutting nodes, or of one and of the plate, does not run, nor does what reads it, and its standing says which. A widget's `set_source` below a served node is handed the served file (region) |
| `def key_params(params) -> a JSON value` | what of its params `run` reads: the same value for any two params under which `run` hands out the same result of the same input. The node is keyed by it in place of its whole params, so a param `run` does not read, a shape of a geometry file that is not the one chosen, moves no key below the node and nothing is computed again for it. A tool without it, or one whose `key_params` raises, is keyed by all its params. One that leaves out a param `run` reads serves results of the params before |
| `def cut_files(video, footage, params) -> paths` | beside `cut_file`: every file the node would serve under some choice of its params, asked of the footage the node reads wherever it sits, served there or not. The player hands their union over the document's cutting nodes to each settings widget with a `set_cut_files_in_use(paths)`, so a card can list the files of its footage that no node of the document uses (region) |
| `STATIC = True` | the output is the same at every row: the memo holds it once under the key and never evicts it while the node stands under that key, and the monitor counts its run per change rather than per row |
| a plane as output | the node's density, v2's plot: its pixels per row counted on a fixed log axis, drawn as a field under the lines in the plot while the node is selected or pinned, for every fed frame node; a mask or a field has none. Its two handles are the node's band, saved with the node: the player zeroes every pixel outside it (inside it when lo is above hi) before anything downstream reads the node |

`tools/` holds a working example of each. A module there whose name begins with `_` is not a tool
but what tools share, the table kind in `_table.py` and its drawing in `_draw.py`; a tool imports
from those and from no other tool, which `tests/test_seams.py` checks. A column a tool adds to a
table goes through `_table.py:with_column` with its unit, one of `wire.py`'s or `wire.NONE`.

## The player

The frame is on the left, the node canvas over the selected node's parameters on the right, and
the timeline across the bottom. The node with the display flag is what the frame shows; the node
with the overlay flag, a second disc offered only on a node producing one plane (`wire.TYPES`),
is heated over it, cold-to-hot in v2's ramp, and a click on the flag it carries turns it off; a
third disc, on a node whose tool has a `draw()`, puts that node on the document's `drawn` list and
takes it off, and the frame paints the `draw()` of the nodes on it and computes for no other; selection
only chooses whose card the pane shows and whose series the plot and the strip draw in colour. A worker thread computes and the GUI thread
reads: every node's output is memoized under a key built from its params and its
upstream, and the display shows what the memo holds.

Each module's docstring says what it does: `document` (the saved form; imports no Qt or cv2),
`graph` (the runtime), `worker`, `canvas`, `pane`, `window`, `timeline`, `theme` (the design
language). `tests/test_seams.py` checks which imports which.

This file describes the code; where the two disagree, the code is what SIEVE does.