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

A tool is one file. Two kinds.

A **frame tool** maps one row to one array:

```python
NAME = "rescale"; KIND = "frame"; EXPECTS = "gray"; PRODUCES = "gray"
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
player compares for equality and never looks inside; stage one must expect `"gray"`. `run` may be
called from a worker thread and the GUI thread at the same time, for any row in any order. A tool
that caches must key on `frames.key` (or `series.key`) and on every one of its own params. A
`"gate"` bool array in a series result is drawn on the frame as a red border while the playhead is
inside a gated row. `run` must need only cv2 and numpy: import Qt and `sieve_player` inside
`settings()` (and inside the `__main__` block), never at module top, so a batch script can import
the tool on a machine with neither installed. `sieve_player.ParamWidget` is an optional base for
`settings()` with `add_int` / `add_float` / `add_bool`; `tools/` holds three examples.

The last tool in a chain may also export. It does so by defining `output_name(src, params) -> path`
and `export_command(src, dst, params, fps) -> argv`; the Outputs section then shows the target and
an Export button that runs the argv in a subprocess, and may show a line from an optional
`describe_output(src, params, fps) -> str`. If the target exists the player writes `name-2.ext`,
`name-3.ext`, and so on; a cancelled or failed run leaves no partial file. A chain whose last tool
has no `export_command` has an Outputs section that says so. `mock-up/downsample/downsample.py`
is the example; it also runs headless with `--out`.

## The player

The right panel is one column: Inputs (cool grey), the tools' settings boxes (white), Outputs
(warm grey). Inputs and Outputs are the player's and look the same in every tool; their names are
drawn top-right as a watermark behind the content, Arial Black where it exists, and take no
layout space. The two greys sit a luminance step apart so they still separate in monochrome.
Until a video is loaded the transport is disabled and the frame is black; load builds the decoder,
chain and worker, and the next load replaces them. A path that won't open is reported in Inputs
and leaves whatever was open alone. `sieve_player/sections.py` holds the sections and the two
widgets; the colours and the watermark style are constants at its top.

Decoding is cv2 to gray with one cursor: sequential reads step it, anything else seeks. Recently
decoded rows sit in a dict bounded by count. Each stage's output per row is memoized under a key
that hashes the tool's params and the upstream key, so a slider change at stage 3 invalidates
stage 3 onward and nothing before. The memo is bounded by bytes and drops image-shaped entries
before small ones.

One worker thread walks the loop window through the chain, writes the last stage's outputs into a
preallocated stack, and hands the growing stack to the series tool every 30 rows. Latest wins: a
frame-tool change restarts the walk, a series-tool change reruns only the series tool on the stack
it has. A display request for a row the memo doesn't hold jumps the queue. The GUI thread never
runs a tool and never waits on the decoder: the display reads the memo, and if the row isn't there
it asks the worker and keeps showing the last frame until it lands.

## The timeline

One full-width strip across the bottom spans the whole recording and carries the playhead and the
loop window. The strip owns neither; it paints what it's told and reports gestures. Press, drag and
release are three signals with three meanings: press and release are commitments and may cost a
decode, a drag is a guess served from the memo or not at all. The window's two edges resize and
its body moves; the strip paints from a local draft during the drag and writes through once, on
release. A click outside the window moves the playhead. A bubble above the cursor shows row and
timecode throughout any drag. The control row above the strip has play/pause, step ±1, loop start
and length in seconds, and a row / timecode / fps readout. Playback loops inside the window.
Space, Left and Right are bound.

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
