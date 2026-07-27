# To Do

**Items live in `docs/todo/`, one file each** — open and deferred alike, with
the trigger in frontmatter; `docs/.state.md` is the generated summary. This
file holds what is *not* an item: the bug list below, and the settled table
open work must not re-decide.

The loop that governs the work — checklist before the first edit, gate,
completion by move, findings kept separate, commit and push — is in
`CLAUDE.md`; what an item looks like is in `docs/todo/_TEMPLATE.md`.

## Bugs and tweaks
Bundle these together to not have to do the full test/gate suites for minor things. Tag them when you notice the diff with the date and time so you know when they popped up and you can track them — the format is `(noticed YYYY.MM.DD)`, and `tests/docs/test_todo_hygiene.py` fails on an untagged entry. `<=` marks the ones that predate the rule.

If any of these are a compounding bug - something that will cause something else to be rewritten if not immediately addressed, address it at the first availability. If it is better at a different time, move it to later, otherwise, todo is fine.

The thirteen below were read against the code on 2026.07.27 and each now has a
file in `docs/todo/` holding the diagnosis, the file:line anchors, and the
ordering. A bullet here is the noticed-date record and a pointer; the item is
the home. **Suggested order:** the four compounding ones first
(ratio-after-undo → wheel → spacebar → band power), then the save/history
policy decision, then the composite-view batch as one pass (zoom first, for its
geometry), then stamp, then the rest.

- The right side panel of filters should be insensitive to mouse scrolls - accidentally scrolling up and down that menu shouldn't also automatically result in a rescale box jumping down or up, normalize changing, block number changing, etc. (noticed <=2026.07.27) → `todo/wheel-over-the-panel.md`
- Spacebar should generally work across the board - if something is changed, like a drop menu or whatever else, spacebar should start working again. (noticed <=2026.07.27) → `todo/spacebar-dies-on-focus.md`
- Blocks in band has the cap at inf but depending on operations done it might have a line that is just crushed to the bottom (noticed <=2026.07.27) → `todo/blocks-in-band-autoscale.md`
- Band power in block may randomly give out if block signal block number is low enough (noticed <=2026.07.27) → `todo/band-power-at-small-block-size.md`
- Video should auto play (noticed <=2026.07.27) → `todo/video-autoplays.md`
- Right click on the video in the filter tab should take it back to the replicate tab full view (noticed <=2026.07.27) → `todo/right-click-back-to-the-replicate-tab.md`
- Instead of shift to peek, it should just let you hover with mouse to peek (noticed <=2026.07.27) → `todo/hover-to-peek.md`
- Stamp should be the default once one is drawn. Stamp should be the default if the user clicks, and if the user tries to drag click it should let it draw. It should stamp based on the highlighted replicate. (noticed <=2026.07.27) → `todo/stamp-as-the-default-gesture.md`
- If the user sets the replicate and tries to change it, it should ask for confirmation as a box. (noticed <=2026.07.27) → `todo/confirm-before-changing-the-replicate.md`
- If the user draws boxes and undoes it, then clicks into a replicate, the ratio is wrong (noticed <=2026.07.27) → `todo/ratio-wrong-after-undo.md`
- It shouldn't ask to save the project or load the project. But it should automatically keep project history so if the user messes stuff up it can roll back. (noticed <=2026.07.27) → `todo/no-save-prompts-keep-history.md`
- The zoom function should work on the replicate tab too. (noticed <=2026.07.27) → `todo/zoom-on-the-composite-view.md`
- We had a beautiful bottom bar previously but it's now gone (noticed <=2026.07.27) → `todo/seeker-upgrades.md`. Not a regression: `gui/timeline_bar.py` is the v2 base (its `STRIP_HEIGHT` comment reserves room for the lanes) and the loaded seeker in `mockups/seeker/` was never built. Resolved 2026.07.27; the item it duplicated is deleted.

## Keeping this file small

This file's job is to be cheap to read. It stopped being that once: a *Build
order* section grew to 190 lines of prose narrating everything already finished,
so finding the two open items meant reading 25 KB of history that
`docs/completed-todo/` already held one entry at a time. The open items
themselves moved out for the same reason — one file per item in `docs/todo/`,
where finishing one is a move instead of an edit here.

So: **history goes to `docs/completed-todo/`, items go to `docs/todo/`, and the
only thing that stays here is what a future item must not re-decide.** That is
the table below, and it is a table because a table cannot grow a paragraph.
When you complete an item, you may add a row; you may not add a section.

---

# What already exists — take it, do not rebuild it

Every row is settled. The third column is the part that costs a day if you
re-derive it. Full reasoning is in the linked entry, and
`docs/completed-todo/.index.md` lists all of them.

| What | Where | What you must not re-decide |
|---|---|---|
| Filter contract | `core/filter_base.py` | `FilterSpec.warmup_frames` is the *bound* over the legal parameter range; `ParamsBase.warmup_frames` is the *configured need*. `node_warmup_frames` picks. Declaring only the bound charges every run for the worst case (7199 frames, in the case that forced the split). |
| Warmup along a path | `core.source_warmup_frames` | It does **not** sum. It walks sink to root converting `need` to `ceil(need / output_rate)`. A plain sum compiles, runs, and under-warms every temporal filter behind a decimator while rendering a plausible frame. |
| Saved artifact | `core/pipeline_model.py` | Schema v3. `Edge.port` names the input it feeds; `Project.detector` and the pin fields landed in v3; v1 and v2 documents still load. |
| Filter discovery | `core/filter_registry.py`, `filters/__init__.py` | A `pkgutil` scan that names nothing. Never add a filter to an import list — a test AST-parses for exactly that. |
| Graph validation and order | `pipeline/dag.py` | One topological order per document, not per traversal. Take `Dag.order`; do not sort a graph again. |
| Pre-run derivation | `pipeline/plan.py` | Resolved params, keys, and the source lead-in as a backward max over `Dag.order`. |
| Cache keys | `pipeline/cache_key.py` | Ports bind each upstream key, so `a - b` and `b - a` are two computations. Sibling branches stay valid when one is edited. |
| Stateful nodes | `filters/background_ema.py` | A stateful node is deliberately **uncacheable**, and not for the obvious reason. Read `findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md` before assuming a key could carry it. |
| Execution | `pipeline/executor.py` | The one loop all three front ends call. `Mode.WINDOWED`, `rate_changing`, and `emits`-more-than-one-stream are still refused at run time. Multi-upstream is **not** — it landed. |
| Re-render on edit | `pipeline/preview.py` | `PreviewSession` pays only for nodes below the edit: 3.3 ms warm against 1350 ms cold. The 3 s ceiling is met by the *store*, not by anything being fast. |
| Decode | `decode/reader.py`, `decode/prefetch.py` | Threading buys 1.61x and stops. The remaining 6x is a 47.6 MB BGR array per frame, not a threading problem. Do not treat decode speed as open without reading both decode findings — and note that every route past it changes what a pixel is and needs a cache generation. |
| Timings | `bench/metrics.py`, `gui/executor_adapter.py` | Qt-free bus; the adapter is the only place that knows both it and Qt. Do not invent a callback to report through. |
| Render thread | `gui/preview_runner.py` | Holds a `PreviewSession` on its own thread with one pending slot. Playhead refreshes are suppressed while a window render is outstanding so they cannot displace it. |
| Coalescing | `gui/coalescer.py` | Two slots, rank rule, source stamp, Qt-free. It lives in `gui/` and `pipeline/` **cannot** inherit it — the layer contract puts `gui` above `pipeline`. |
| Time selection | `gui/timeline_model.py` | `ReplicateDocument.clip` is the chosen span and `SetClip` is its only writer; `window` is the derived view that falls back to ten seconds. Arithmetic is Qt-free. |
| Plots | `gui/band_plot.py` and its specializations | QPainter, not pyqtgraph, not napari. See *Deferred decisions*. |
| Block signals | `filters/block_signal.py` | Emits `change_energy`, `flow_speed`, and `coherence`. The solve precedes block reduction; reduce the *tensor*, then eigendecompose. The spec's drafted coherence scalar was wrong — see `findings/2026.07.26-the-specs-coherence-formula-fails-its-own-test.md`. |
| Threshold units | `filters/temporal_baseline.py` | Median and MAD over a trailing window, because the events are in the sample. The estimate lags a step change by about one window; a centred one needs `Mode.WINDOWED`, which is refused. |
| The crop | — | It belongs in the graph, and the per-replicate threshold-spread probe that would have measured one rack under one backlight is cancelled, not deferred. `findings/2026.07.25-the-crop-belongs-in-the-graph.md`. |
| Crop gestures | `gui/video_view.py` | Handles are hit-tested *before* containment, and only on the selected box. Drawing needs travel in both axes; adjusting needs it in either — a horizontal move under the both-axes rule releases as a click and navigates away. `view_rect` is the mapping, `content_rect` is only the floor it is clamped against. |
| Placement | `gui/video_view.py` `_placed` | A stamp or a move slides against the frame edge and never trims. `ROI.clamped_to` is the *other* rule and belongs to typed numbers, not to placements. |
| One drag, one undo | `gui/commands.py` | `SetReplicateROI` merges on a per-press token, and `mergeWith` keeps the *first* command's displaced value. A test that drags with a single mouse-move cannot see any of this — the second event is a no-op `set_roi` and the count is 1 either way. |
| One action, many rows | `gui/commands.py` `SetReplicateROIs` | Merging cannot produce this. `mergeWith` only joins commands naming the *same* row, so a loop pushing one command per replicate is one undo entry per replicate whatever token it carries. A batch edit is one command holding many rows. |
| Slide versus trim | `core/types.py` `ROI.placed_in` | The rule that a region keeps its exact extent and moves, used by both the stamp and "Set all". `clamped_to` is the other rule and trims. Reaching for the wrong one at the frame edge silently makes a rack non-uniform while every number on screen says it worked. |
| Settings memory | `core/pipeline_model.py` `edited_params` / `edited_detector` | The two-write edit: pin the diff on the replicate being looked at, move the baseline for everyone following. Submit only the fields touched — a whole resolved view drags a deviated arena's pins into the baseline. The GUI routes through `ReplicateDocument.edit_params`/`edit_detector`; the tab's `LiveChain` is the resolved *view*, never a second store. |
| Detector in the artifact | `core/pipeline_model.py` `DetectorSettings` | Schema v3. Bands, count threshold, and D live on `Project.detector` with field-level pins in `Replicate.detector_overrides`; `solo_block` is looking, not tuning, and stays out. `None` means never tuned — do not resolve the fps-derived default into the field. |

---

## Deferred decisions

- **napari and `pyqtgraph` are out of the `gui` extra, and stay out** (closed
  2026.07.26). The filter-tab plot family landed as QPainter widgets over
  `gui/band_plot.py`, and the last item owning a napari question — the three-way
  overlay — answered it by collapsing to two layers and one opacity slider.
  Re-adding either needs a new demand, not a revisit.
- **`gui/state.py` was not created.** Scrub position and playing state live in
  `VideoPlayer`; a separate object would duplicate them. Create it when there is
  UI state with no natural owner (panel layout, zoom) — which the crop-tools item
  above may produce.
- **`ARCHITECTURE-TREE.md` does not exist and no longer obviously should.**
  `docs/findings/` holds measurement-driven decisions one file at a time and
  `docs/completed-todo/` holds what was built.
- **`src/sieve/docs/` never existed.** The eight interface specs `SIEVE-HANDOFF.md`
  used to ask for are module docstrings plus their completed-todo entries, and
  the handoff now says so.
- **`hypothesis` is used by four modules under `tests/property/`.** The
  test-selection rule in `CLAUDE.md` narrows what earns one going forward; the
  existing four stay.
