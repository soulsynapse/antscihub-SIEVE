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

Not committed — awaiting permission.

---

## GUI tests

`tests/gui/` has a `conftest.py` and nothing else. The tab was verified by a
throwaway script, which is not a regression test.

Cover with pytest-qt (`QT_QPA_PLATFORM=offscreen`, CI already sets it):
undo/redo across `AddReplicate`, `RemoveReplicate`, `RenameReplicate`,
`SetReplicateROI`; `ReplicateTableModel.setData` routing through the undo
stack and rejecting a zero-extent ROI; `VideoView` widget↔source coordinate
round-trip; `EditingAwareDelegate` disabling the space bar while a cell editor
is open.

Read: `src/sieve/gui/{document,commands,replicate_table,video_view}.py`.

## Pyright on gui

`nox -s typecheck` has not been run since `gui/` was added. PySide6 stubs
under `typeCheckingMode = "strict"` (see `pyproject.toml`) will need either
fixes or a scoped relaxation for `src/sieve/gui/**`. Pick one deliberately;
don't leave the session failing.

## Scrub budget miss

A single random seek costs ~80 ms against the 50 ms `scrub_to_repaint` budget.
Request coalescing makes scrubbing *feel* right (40 seeks settle in 172 ms)
but the per-seek number is still a miss, and non-negotiable #4 says a miss is
a defect not a tradeoff.

Pick one: scrub-resolution proxy decode, keyframe-only mode while the slider
is down, hardware decode, or an explicit amendment to the budget in
`ARCHITECTURE.md`. Then assert it in `bench/`.

Read: `docs/FINDINGS.md`, `src/sieve/decode/reader.py`, `src/sieve/gui/player.py`.

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
