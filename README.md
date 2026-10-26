# SIEVE — Signal Isolation of Ethological Video Events

SIEVE chains independent video-analysis scripts and gives them one shared, polished UI so each
script doesn't need its own GUI. The scaffold is `sieve_player`: a PySide6 window with the video on
the left, a three-section panel on the right (inputs, the script's own settings, outputs), and a
timeline across the bottom. A script imports it and runs standalone:

```python
if __name__ == "__main__":
    from sieve_player import play
    play([sys.modules[__name__]])   # or play([rescale, threshold, motion]); the player knows no tool by name
```

`play` opens empty and never prompts; the video is picked in the Inputs section, or passed as the
second argument. Picking again replaces it.

```
py -3.13 -m venv .venv            # not the Anaconda python: its Qt DLLs shadow PySide6's
.venv\Scripts\python -m pip install -r requirements.txt     # editable install of sieve_player
.venv\Scripts\python main.py video-tests\rep3_intermittent_crop.MP4
.venv\Scripts\python tools\motion.py video-tests\rep3_intermittent_crop.MP4   # any tool runs alone, from any cwd
.venv\Scripts\python smoke.py video-tests\rep3_intermittent_crop.MP4          # offscreen: open, load, export, reload
```

## What a tool is

A tool is one file, marked `SIEVE_TOOL = True` and named by `NAME`; nothing else is required for
`sieve_player.registry` to list it, and everything else below is a facet it may or may not have yet.
The registry's own README is the spec for how tools are found and probed. Two kinds.

A **frame tool** maps one row to one array:

```python
NAME = "threshold"; KIND = "frame"; EXPECTS = "gray"; PRODUCES = "gray"
DEFAULTS = {...}                              # plain JSON-able dict
def run(frames, row, params) -> np.ndarray    # frames(r) is the upstream output at row r
def settings(parent=None) -> QWidget          # has .changed (Signal) and .params() -> dict
```

A **series tool** sees the whole loop window at once, and there is at most one, last in the chain:

```python
KIND = "series"; EXPECTS = "gray"
def run(series, params) -> dict               # series.data is (T, ...), the upstream outputs stacked
def settings(parent=None) -> QWidget          # .changed, .params(), .show_result(result, start, fps), .set_playhead(row)
```

`frames.key` / `series.key` names the input and changes whenever anything upstream changes;
`frames.fps`, `frames.count`, `series.start` are facts. `EXPECTS` / `PRODUCES` are strings the
player compares for equality and never looks inside. The decoder produces `"bgr"`; `tools/gray.py`
turns it into `"gray"` for the tools that want luma. `EXPECTS` may be a tuple of types, and
`PRODUCES = "same"` means out as in (rescale, downsample). A tool reads one earlier stage, by
default the nearest one whose product it expects, the video counting as a stage; a chain in which
some tool can read nothing before it is refused. The player lets you point a tool at any earlier
stage of the right type (`sieve_player.chain.Links`), so a chain is a list that reads as a graph:
a stage nobody reads is still computed when shown, and nothing else; a stage with no input is
computed as None. `run` may be
called from a worker thread and the GUI thread at the same time, for any row in any order. A tool
that caches must key on `frames.key` (or `series.key`) and on every one of its own params. A
`"gate"` bool array in a series result is drawn on the frame as a red border while the playhead is
inside a gated row. `run` must need only cv2 and numpy: import Qt and `sieve_player` inside
`settings()` (and inside the `__main__` block), never at module top, so a batch script can import
the tool on a machine with neither installed. `sieve_player.ParamWidget` is an optional base for
`settings()` with `add_int` / `add_float` / `add_bool`; `tools/` holds the examples.

Any tool may draw on the frame by defining `draw(painter, row, result, start)`. The player calls
it after painting the frame and the gate border, with a `QPainter` whose coordinates are the
pixels of the displayed array, so a pen of width 0 stays one screen pixel and any other width is
in frame pixels. `result` is the series result or None, `start` the row it begins at, `row` the
row on screen. A `draw` that raises is reported once and dropped for the session. Qt is imported
inside `draw`, like `settings()`. `mock-up/lk_flow/lk_flow.py` draws its tracks this way.

The last tool in a chain may also export. It does so by defining `output_name(src, params) -> path`
and `export_command(src, dst, params, fps) -> argv`; the Outputs section then shows the target and
an Export button that runs the argv in a subprocess, and may show a line from an optional
`describe_output(src, params, fps) -> str`. If the target exists the player writes `name-2.ext`,
`name-3.ext`, and so on; a cancelled or failed run leaves no partial file. A chain whose last tool
has no `export_command` has an Outputs section that says so. `tools/downsample.py` is the
example; it also runs headless with `--out`.

## The player

The window follows the design language settled in `mock-up/design-language` and carried by
`sieve_player/theme.py`: everything sits on a dark ground, each box on it is one fixed step
lighter, nothing is inset past the third step, and the only white is a section's name. The right
column is the chain, a stack of such cards: Inputs, one per tool, Outputs, with the accent arrow
running out of the bottom of each card into the top of the one that reads it, at the left under
the names; the strip between them says what the lower card receives and from where. An arrow
whose source is not the card above jogs out into the gutter and back. A frame tool's output
that nothing reads and no file takes ends in a red bar instead, with "unread" beside it. The two
end cards are told from the tool cards only by their hairline, teal for Inputs and salmon for
Outputs, about as bright as the gray it replaces. A tool's name is dotted-underlined: it is a
link. Clicking it, or double-clicking the card, opens the tool alone: an Input card above with a
picker of the stages it may read, or nothing; the tool; an Output card below with a checkbox per
later stage that expects what this one hands out, checked if it reads it, and a line saying what
reads it, red if nothing; and the frame showing this stage's output, which it keeps showing after
the tool is closed: the card named in the accent is the one on the frame, so clicking a card is
also how the frame is pointed at a stage. Input and Output are one wiring seen from both ends:
unchecking a reader leaves it with no input, and a stage with no input is computed as nothing,
says "no input" in red above it, and blanks the frame, with that line, while the tool is open.
Closing the tool with the shown stage unfed, or any wiring that leaves it so, moves the frame to
the last stage the video reaches. Knobs and both pickers act at
once; Save or a right-click anywhere keeps them, Cancel or Escape puts them back. Pointing a pass-through
tool at a stage of another type can change what later tools receive; each one left with a type it
does not expect loses its input. The
transport across the bottom is one more surface. Inside
a surface a form is a table, descriptions left-aligned in a column sized to the widest, every
control one width and one height in the next. Editable controls are wells the ground shows
through; what the pipeline measured is a flat field lifted above the surface, so depth alone
says what can be touched. The accent marks the flow and what is viewed: the arrow, the loop window on the
strip, the trace; amber marks the gate. `ParamWidget` builds such a form and `Trace` draws a series in
it: the trace in the accent, the playhead white, the gate amber. Inter is bundled and loaded
first so Mac and Windows render alike; on Windows the player asks for FreeType, since DirectWrite
ignores the hinting preference and fringes on a dark ground. Until a video is loaded the transport
is disabled and the frame is empty; load builds the decoder, chain and worker, and the next load
replaces them. A path that won't open is reported in Inputs and leaves whatever was open alone.
`sieve_player/sections.py` holds the Inputs and Outputs widgets.

Decoding is cv2 to BGR with one cursor: sequential reads step it, anything else seeks. Recently
decoded rows sit in a dict bounded by count. Each stage's output per row is memoized under a key
that hashes the tool's params and the upstream key, so a slider change at stage 3 invalidates
stage 3 onward and nothing before. The memo is bounded by bytes and drops image-shaped entries
before small ones.

One worker thread walks the loop window through the chain, writes the series tool's source stage
(or, without one, the shown stage) into a
preallocated stack, and hands the growing stack to the series tool every 30 rows. Latest wins: a
frame-tool change restarts the walk, a series-tool change reruns only the series tool on the stack
it has. A display request for a row the memo doesn't hold jumps the queue. The GUI thread never
runs a tool and never waits on the decoder: the display reads the memo, and if the row isn't there
it asks the worker and keeps showing the last frame until it lands.

## The timeline

One full-width strip across the bottom spans the whole recording and carries the playhead and the
loop window. The strip owns neither; it paints what it's told and reports gestures. Press, drag and
release are three signals with three meanings: press and release are commitments and may cost a
decode, a drag is a guess served from the memo or not at all. A handle along the window's top edge
moves it; its length is set only in the control row. The strip paints from a local draft during the
drag and writes through once, on release. A press in the field outside the window puts the window's
front at the click, playhead at the front, and goes on as a drag. A click in the band below the
handle moves the playhead; playback pauses while it is held and resumes on release. The playhead is
never outside the window: a drag, step or arrow key that would leave it is clamped to the nearer
edge, and a handle move or spinbox edit carries the playhead with its offset from the start. A
bubble above the cursor shows row and timecode throughout any drag. The control row above the strip
has play/pause, step ±1, loop start and length in seconds, and a row / timecode / fps readout. A
load starts playback, which loops inside the window. Space, Left and Right are bound.

## STATUS

**2026-10-11** — first cut. `sieve_player` is 796 lines over seven modules. Numbers from
`bench.py` (headless, chain only, no Qt) on `video-tests/rep3_intermittent_crop.MP4`
(462×456, 59.94 fps), chain rescale 0.5 → threshold → motion, 600-row window, one run:

| measurement | result |
|---|---|
| fill 600 rows (decode + rescale + threshold) | 0.16 s, 600 decodes, 0 seeks, 60 MB memo |
| re-walk with nothing changed | 0.6 ms |
| threshold drag (stage 2 reruns on memoized rescale output) | 15.7 ms |
| rescale drag (stages 1–2 rerun) | 0.25 s, 600 more decodes |
| decodes equal rows walked on fill | yes (asserted) |

The rescale drag re-decodes every row because the decoder cache holds 256 rows and the walk is
forward LRU, so by the time the walk restarts the window's early rows are gone. That is the design
as specified; raising `Decoder(cache_rows=...)` to the window length makes a rescale drag cost
about what a threshold drag does. In the GUI, playback at 60 fps advanced 87 rows in 1.5 s while
the worker was still filling; three scripted runs (strip drag, 1.5 s playback, screenshot) completed
identically.
