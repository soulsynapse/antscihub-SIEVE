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
.venv\Scripts\python tools\motion.py [video]             # any tool runs alone
.venv\Scripts\python smoke.py video                      # offscreen end-to-end check
.venv\Scripts\python -m pytest
.venv\Scripts\python -m sieve_player.registry --check    # the tools, their facets, the types they use
```

## A tool

A tool is one Python file with `SIEVE_TOOL = True` and a `NAME`. Everything else is a facet it may
or may not declare; `sieve_player/registry/README.md` says how tools are found and what a missing
facet means, and `python -m sieve_player.registry` lists the facets the player reads.

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
def settings(parent=None) -> ParamWidget      # optionally show_result(result, start, fps), set_playhead(row)

# a series tool reading another: EXPECTS = "signal", and series.data is the upstream result's
# "signal" with the rows its band shuts out zeroed (smooth).

# a selector: which file, by rule
NAME = "file"; KIND = "selector"; PRODUCES = "path"
def select(folder, params) -> str | None      # folder is the document's
```

How the player treats a tool, as `sieve_player/graph.py`, `pane.py` and `window.py` currently do:

- Types are strings the player compares for equality; it attaches no meaning to them beyond the
  video node producing `"bgr"`. An `EXPECTS` tuple accepts any of its members, and
  `PRODUCES = "same"` hands out whatever the tool reads.
- Only the worker thread calls `run`, but for any row in any order, since a seek jumps its queue.
  `frames.key` / `series.key` changes whenever anything upstream does; the tools that cache key on
  it and on their own params.
- The tools under `tools/` import Qt and `sieve_player` inside `settings()`, `draw()` and their
  `__main__` block rather than at module top, which lets a script without Qt import them and call
  `run`.
- The document holds the params. The pane moves a settings widget's knobs to them with
  `set_params()` and writes `params()` back on every change; `ParamWidget` provides both, and a
  widget without them is shown as a defect.
- Each node reads one node through a wire. A node the video does not reach, through wires whose
  types fit, computes as None, and so does everything downstream of it.
- Series nodes run as a chain: the first one reading a frame node runs on the stacked window, and
  each fed series node wired on from a chain node runs after it on the upstream result's
  `"signal"`. A second series node reading a frame node does not run.
- A series tool's `fold(frame)` runs on the worker as each row is computed and takes no params: a
  change to the tool's params reruns `run` on the stack already folded, so a fold must hold every
  number any params could ask for (reduce folds a row to its sum, max, count and size).

Facets the player reads when a tool has them:

| facet | what the player does with it |
|---|---|
| `draw(painter, row, result, start)` | paints on the frame, in frame-pixel coordinates (`painter.window()` is the frame's rect); one that raises is dropped for the session |
| a `"signal"` array in a series result | the node's trace, drawn as a detector. Its two handles are the node's band, in the signal's units, saved with the node: the player adds `"gate"`, the rows inside it (outside when lo is above hi), washes them on the trace, zeroes the rest of the signal before a series node downstream reads it, and draws a green border on the frame while the playhead is in a row the last chain node gates |
| `output_name`, `export_command`, `describe_output` | an Export button on the node; an existing target gets a numbered sibling, and a failed run leaves no partial file |
| `PATHS = {input: loader}` | a path input a selector feeds; the loader turns the file into params |
| a plane as output | the node's density, v2's plot: its pixels per row counted on a fixed log axis, under its settings, for every fed frame node; a mask or a field has none. Its two handles are the node's band, saved with the node: the player zeroes every pixel outside it (inside it when lo is above hi) before anything downstream reads the node |

`tools/` holds a working example of each.

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
language from `mock-up/design-language`). `tests/test_seams.py` checks which imports which.

This file describes the code; where the two disagree, the code is what SIEVE does.