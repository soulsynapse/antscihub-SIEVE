# To Do

## Rules

1. Todo items are given a short (<5) word name.
2. Todo items are written so you don't have to load all the docs, when possible.
3. Todo items scope target is <150k context window
4. When todo items are done, do the commit and let the user know they can clear.

---

## Done — Replicate tab (2026-07-25)

Built: `core/` (ROI, Frame, ChannelSpec, VideoMetadata, Replicate,
ReplicateSet) · `decode/` (VideoReader, decoder_identity) · `bench/budgets.py`
· `gui/` (Replicate tab, 50/50 splitter, File/Edit/Playback menus,
drag-to-cut, threaded decode, QUndoStack) · `.importlinter` with 4 contracts
wired into `nox -s checks`.

Run it: `uv run sieve-gui` or `uv run sieve-gui videos-testing/<clip>.MP4`.

48 tests pass. `ruff` and `lint-imports` clean. Verified headless against the
5.3K clip: open 213 ms, 40-seek scrub burst settles in 172 ms, playback holds
real-time speed at 36.5 rendered fps, undo/redo round-trips all four commands.

---

## Done — GUI tests (2026-07-25)

`tests/gui/` now carries 85 pytest-qt tests: undo/redo round trips for all four
commands including identity survival, `ReplicateTableModel.setData` routing and
its rejection paths, the `VideoView` letterboxed coordinate mapping and drag
interpretation, and the editor guard end to end through a real `MainWindow`
with the synthetic video open. Shared mouse-event helpers live in
`tests/gui/qt_input.py`. 133 tests pass; `ruff` and `lint-imports` clean.

Two things changed outside the tests. `VideoView._content_rect/_to_source/
_to_widget` are now public (`content_rect`, `to_source`, `to_widget`) — the
mapping is the widget's service to its callers, and box-dragging will need it
for hit-testing. And the `pytestmark` in `tests/gui/conftest.py` was inert:
pytest reads `pytestmark` from test modules and classes only, so the `gui`
marker is now declared per module.

Checked by mutation: breaking the editor guard, the letterbox offset, or the
rename's undo push each fails a test.

## Done — Pyright strict (2026-07-25)

`nox -s typecheck` is clean: 0 errors, no `# type: ignore`, no per-directory
relaxation. All 8 were real, and each was fixed at the source rather than
silenced.

One was a latent bug. `ChannelSpec.count` shadowed `str.count` on a `StrEnum`,
so `ChannelSpec.BGR.count("b")` returned 3 instead of 1 — any caller treating
the spec as the string it is would have been silently wrong. Renamed to
`channel_count`, with a test pinning `str.count` intact.

The rest were honesty fixes: `_downscale` claimed `NDArray[uint8]` while doing
nothing to guarantee it (now `NDArray[Any]`, matching its input); `read()`
tested `data is None` alongside `not ok`, which OpenCV never produces
separately; `setShortcuts` was handed a bare `StandardKey` (now wrapped in
`QKeySequence`); and three `selectionModel() is None` guards in
`ReplicateTab` were dead — `setModel` runs in the constructor before any of
them.

134 tests pass; `ruff`, `lint-imports`, and `pyright` all clean.

## Done — Scrub budget and Preferences (2026-07-25)

The budget miss is closed, by measurement rather than by amendment alone. Both
remaining escape hatches were probed and shut: hardware acceleration does not
engage in this OpenCV build, and keyframe alignment buys nothing (no sawtooth
in seek cost across 150 consecutive targets). The seek is 46.7 ms of a 67.8 ms
total and has no knob.

So `scrub_to_repaint` moved 50 → 100 ms and is now *enforced by degrading*:
`gui/scrub_policy.py` watches the median of the last 5 scrub round trips and,
above budget, snaps drag targets to a 1 s grid that `gui/frame_cache.py`
serves for free. New `scrub_settle` budget (250 ms) covers the release, which
always decodes the exact frame. Coalescing now carries request *intent* —
a pending exact seek is never dropped for a later drag position, which was a
real bug the tests caught.

Also added: `gui/preferences.py` (QSettings, 3 settings, all consumed),
`gui/preferences_dialog.py` (Edit → Preferences…, applies on change), and
`gui/toast.py` — the bottom-right notice that tells the user once when coarse
mode engages.

181 tests pass; `ruff`, `pyright`, and `lint-imports` clean.

Note the naming: the notice says "coarse seek", not "keyframe seek", because
the measurement says keyframe alignment is not the mechanism.

Read: `docs/FINDINGS.md` §"The seek is irreducible".

## Persist replicates

Replicates live only in memory and die with the window. They are DAG nodes
(VISION step 2), so this is the first real use of the pipeline artifact.

Needs `core/pipeline_model.py` (pydantic v2 → YAML) and a decision on where a
project file lives relative to the source video. Blocks anything that has to
survive a restart. Guardrail to honour: no GUI-only state in the artifact.

Read: `docs/AUTO-GUARDRAILS.md` §2, `src/sieve/core/replicates.py`.

## Representative clip range

The tab cuts space; the workflow also needs the 5–10 s clip that in-pipeline
tuning runs against. In/out points on the transport bar, stored per replicate
or per project — decide which. Feeds `pipeline/preview.py` later.

Read: `docs/VISION.md` step 4, `src/sieve/gui/replicate_tab.py`.

## Drag existing boxes

Boxes can be drawn, renamed, numerically edited, and deleted, but not moved or
resized on the video. Needs corner/edge handles, hit-testing, and
`QUndoCommand.mergeWith` so one drag collapses to one undo step rather than
one per mouse-move.

Read: `src/sieve/gui/{video_view,commands}.py`.

## Build the CLI

`ARCHITECTURE.md` calls the CLI the canonical run path, "built and tested
before GUI". It does not exist. Typer app with `sieve inspect` at minimum, so
the layer contract's optional `sieve.cli` layer stops being hypothetical.

Read: `docs/SCAFFOLD.md` `cli/` section, `.importlinter`.

---

## Deferred decisions

- **napari is in the `gui` extra but unused.** The viewport is a plain
  `QWidget` + `QPainter`: ~150 lines, no dependency, full control over ROI
  overlay and letterboxing. napari earns its place when the preview needs
  layered overlays with independent opacity (VISION step 4's three-way overlay
  switch). Adopt it there or drop it from the extra.
- **`gui/state.py`** from SCAFFOLD was not created. Scrub position and playing
  state live in `VideoPlayer`; a separate object would duplicate them. Create
  it when there is UI state with no natural owner (panel layout, zoom).
- **`ARCHITECTURE-TREE.md`** does not exist. `FINDINGS.md` is absorbing
  measurement-driven decisions. Merge or split deliberately.
