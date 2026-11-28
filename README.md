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
.venv\Scripts\python -m sieve_player.registry            # the tools, their facets, the types they use
.venv\Scripts\python -m sieve_player.registry --check    # that list held to the code
```

What the player prints to stderr, tracebacks, Qt warnings, the watchdog's and a crash's stacks, it
also writes to a log, the previous launch's kept beside it as `.prev.log`; `SIEVE_LOG` names the
file or, as `0`, turns it off, and `sieve_player.dev.console.log_path` says where it goes unset. `SIEVE_DUMP`
names a file every video opened dumps the probe's stream to (`sieve_player/trace.py`);
`SIEVE_QT_TRACE` narrows the Qt warning handler to warnings containing its text, or `0` leaves
Qt's own printing alone; `SIEVE_C_STDERR=1` leaves C-level stderr alone, so libav says
why a stream ended where it did, which the player's own
line at the correction cannot. `SIEVE_MEMO_GB` and `SIEVE_CACHE_GB` set the memo's and the
decoder cache's limits; unset or `0`, each is its share in `sieve_player/budget.py` of half the machine's
memory, or of `SIEVE_MEMORY_GB` where that is set, and the line the player prints on opening a video says
what both are.

## A tool

A tool is one Python file with `SIEVE_TOOL = True` and a `NAME`. Everything else is a facet it may
or may not declare. This file shows the shape of each kind of tool and no more; what every facet is
and what the player does with it is said where it is held to the code:

- `python -m sieve_player.registry` prints every facet the player reads, each with the line a tool
  writes to supply it, and what a settings card may have.
- `sieve_player/registry/README.md` says how tools are found, what a missing facet means, and the
  rules a cutting tool, a selector and a stepping tool follow.
- `tools/` holds a working example of each; a tool there is the reference for its kind.

A tool does one thing, and a wanted variation is a second tool wired beside it, never a knob on
the first: applying one node's output to another's is a node of its own that reads both, not a
setting hidden on either. Chains get longer; tools do not get wider.

```python
# a frame tool: one row in, one array out (threshold)
NAME = "threshold"; KIND = "frame"; EXPECTS = "gray"; PRODUCES = "mask"
PARAMS = {"thresh": {"default": 128, "kind": "int", "range": (0, 255)}}   # every param, once: the node's first
                                              # params and its card are made of it
def run(frames, row, params) -> np.ndarray    # frames(r) is the output of the node it reads, at row r, read-only

# a series tool: the whole window at once (reduce)
NAME = "reduce"; KIND = "series"; EXPECTS = ("gray", "mask"); PRODUCES = "signal"
def fold(frame) -> np.ndarray                 # optional: what the walk stacks per row in place of the frame
def run(series, params) -> dict               # series.data is the read node stacked; the dict carries "signal"
def step(state, row, i, params) -> (state, dict)  # optional: row by row, equal to run over the same rows (travel)
def settings(parent=None) -> ParamWidget      # optional: a card of the tool's own in place of the one made of PARAMS

# a series tool reading another: EXPECTS = "signal" (smooth), or "tracks" for a table a row (travel)

# a frame tool with more inputs: INPUTS = {"diff": "gray"}, read as frames(row, "diff") (blobs)

# a selector: which file, by rule (file)
NAME = "file"; KIND = "selector"; PRODUCES = "path"
def select(folder, params) -> str | None

# a cutting tool: what it reads cut in rows, in pixels or in both, every node below run inside each cut
NAME = "period"; KIND = "frame"; PRODUCES = "same"
CUT_BY = {"gate": ("signal", "tracks")}       # optional: a wire whose result cuts (period)
def cut_extents(params, result, count) -> list  # one dict a cut; with no run each row goes down as it was read
```

What a tool's author is held to and no facet says:

- Only the worker thread calls `run`, for any row in any order. A read that raises
  `graph.Cancelled` or `decoder.EndOfStream` is let through, never swallowed; their docstrings say
  when each is raised.
- A read before row 0, or outside the rows of the cut in time the node runs in, is None: the row is
  absent, and a tool says what it does across one.
- A tool under `tools/` imports Qt inside `settings()`, `draw()` and its `__main__` block, never at
  module top, so a script without Qt can import it and call `run`.
- A module under `tools/` whose name begins with `_` is not a tool but what tools share; a tool
  imports from those and from no other tool, which `tests/test_seams.py` checks.
- A type is a string, a row of `sieve_player/wire.py`'s table; a new one is added there first.

## The player

The frame is on the left, the node canvas over the selected node's parameters on the right, and
the timeline across the bottom. A worker thread computes and the GUI thread reads: every node's
output is memoized under a key built from its params and its upstream, and the display shows what
the memo holds. Why a node does not run is its standing, one line the runtime states per node: the
pane shows it under the node's settings, the canvas as its tooltip, and `--plan` prints it.

Each module's docstring says what it does: `document` (the saved form; imports no Qt or cv2),
`plan` (what will be computed, read off the document and the tools), `graph` (the runtime),
`worker`, `canvas`, `pane`, `window`, `timeline`, `theme` (the design language).
`tests/test_seams.py` checks which imports which.

This file describes the code; where the two disagree, the code is what SIEVE does.
