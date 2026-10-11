# poc — SIEVE v0.4 as a player, standalone tools, and one window

Started 2026-10-11 to test one claim: a tool can be a function and a widget
in one file, know nothing about SIEVE, run on its own, and still give a
tuning loop whose graphs refill faster than the video plays. Nothing in
`src/` or `experiments/` is imported. Measurements go in **Status** below,
dated, so a later one supersedes rather than argues.

## Layout

```
poc/
  sieve_tool/      the player package. A tool's standalone.py imports it; so does the app.
    source.py      cv2 decode, gray, with a hold dict of recent rows        (hook 1)
    chain.py       stages memoized by (stage, row, params-key)              (hook 2)
    player.py      image, slider, loop window, the tools' widgets, series worker
  tools/<name>/
    tool.py        NAME, KIND, DEFAULTS, run(), settings()  — the author's file
    standalone.py  sys.path + play([upstream tools..., tool])
  sieve_app/main.py  one window: folder of videos, tools found by path, opens the player
```

## The rules (this is the whole contract; it does not get a second page)

A frame tool:

```python
NAME = "rescale"; KIND = "frame"; DISPLAY = "image" | "grid"
DEFAULTS = {...}                       # plain JSON-able dict
def run(frames, row, params) -> np.ndarray   # frames(r) is the upstream output at r;
                                             # frames.key, frames.fps, frames.count are facts
def settings(parent=None) -> QWidget         # has .changed (Signal) and .params() -> dict
```

A series tool:

```python
KIND = "series"
def run(series, params) -> dict        # series.data is (T, ...) stacked upstream output;
                                       # series.key, series.fps, series.start
def settings(parent=None) -> QWidget   # .changed, .params(), .show_result(result, start, fps), .set_playhead(row)
```

`run` may be called from a worker thread and must not touch the GUI. It may
be called for any row in any order; if it caches, it keys on `frames.key`
(or `series.key`), which changes whenever anything upstream changes. A
`"gate"` array in a series result is drawn on the player as a red border.

## What the five tools are

rescale, normalize, background ema, block signal (change energy), detect
(Morlet band power → value band → blocks in band → windowed mean →
threshold → gate → intervals). All ported from v2 `filters/` and
`core/ops/`, arithmetic intact, machinery removed. Detect's settings widget
is the scalogram, density and count plots with draggable handles.

## What SIEVE is here

`sieve_app/main.py`: pick a folder, double-click a video, the player opens
with the checked tools as its chain. It imports no tool by name; it globs
`tools/*/tool.py`. That file plus `sieve_tool/` is SIEVE.

## What was deliberately not built

- crops / replicates: the player would hand `frames(r)` already cropped;
  tools would not change. Next thing to add, not needed to test the claim.
- saving params per folder, CSV/annotated export, materialize.
- the hook for "a stage that depends on the source and not on params"
  (precompute). background ema's internal checkpoints are the first case of
  state; the second tool that needs state is when the pattern lifts into
  the player.
- the trace as a file. `Chain.report()` is printed to the status bar once a
  second. Writing it to JSON is one line, when there is a reader for it.

## Status

- 2026-10-11, rep3_intermittent_crop.MP4 (462x456, 59.94 fps), scale 0.5,
  block 16, headless: the four frame stages over 600 rows walk in 0.66 s
  (about 1.1 ms/row, decode included); the series tool over (600, 225)
  runs in 25 ms; a value-band or threshold retune reruns in ~1 ms (band
  power cached). The window plays in 10 s.
- 2026-10-11, same clip, in the player on the desktop (scratch script
  drove it): the 600-row window filled with all five stages in under 6 s
  including 20 partial detector passes; a threshold drag reran only the
  detector (one run, ~16 ms); an EMA alpha drag reran ema and block signal
  (601 → 1202 runs each) and nothing before them, decodes stayed at 600.
  Playback at 60 fps while the window was already filled stayed smooth.
