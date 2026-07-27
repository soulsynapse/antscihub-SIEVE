# To Do

Open work, scoped and startable. Nothing here is done — a finished item is
*moved*, never marked.

The loop that governs this file — checklist before the first edit, gate, atomic
completion, findings kept separate, commit and push — is in `CLAUDE.md`. This
file holds only what an item is and which items are open.

## What an item here looks like

1. A short name, under five words.
2. Written so the work can start **without loading the whole doc tree**. If an
   item needs three documents read before the first edit, it is not scoped yet.
3. Scoped to fit one context window.
4. **Gating stated explicitly**, in a `Gated on:` line — including
   `Gated on: nothing structurally`, which is information.
5. Ending with a `Read:` line naming the files, so the first act is opening
   them rather than searching for them.

Work that is real but not yet timely goes to `docs/LATER.md` with the trigger
that would make it takeable. An item that fails rules 2 and 3 would sit here
growing stale, so it belongs there instead and is *moved* here when the trigger
fires.

## Keeping this file small

This file's job is to be cheap to read. It stopped being that once: a *Build
order* section grew to 190 lines of prose narrating everything already finished,
so finding the two open items meant reading 25 KB of history that
`docs/completed-todo/` already held one entry at a time.

So: **history goes to `docs/completed-todo/`, and the only thing that stays here
is what a future item must not re-decide.** That is the table below, and it is a
table because a table cannot grow a paragraph. When you complete an item, you
may add a row; you may not add a section.

---

# What already exists — take it, do not rebuild it

Every row is settled. The third column is the part that costs a day if you
re-derive it. Full reasoning is in the linked entry, and
`docs/completed-todo/.index.md` lists all of them.

| What | Where | What you must not re-decide |
|---|---|---|
| Filter contract | `core/filter_base.py` | `FilterSpec.warmup_frames` is the *bound* over the legal parameter range; `ParamsBase.warmup_frames` is the *configured need*. `node_warmup_frames` picks. Declaring only the bound charges every run for the worst case (7199 frames, in the case that forced the split). |
| Warmup along a path | `core.source_warmup_frames` | It does **not** sum. It walks sink to root converting `need` to `ceil(need / output_rate)`. A plain sum compiles, runs, and under-warms every temporal filter behind a decimator while rendering a plausible frame. |
| Saved artifact | `core/pipeline_model.py` | Schema v2. `Edge.port` names the input it feeds; a v1 document still loads. |
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

---

# Open items

Two, plus two living in the parity plan (below). The temporal chain that
`docs/REFINED-VISION.md` decomposes into is otherwise complete: coherence,
multi-upstream kernels, and the per-block baseline have all landed, in that
order and for the reasons that document's **Build order** section gives.

## The motion history filter

**Gated on: nothing structurally** — single-upstream, streaming,
rate-preserving and stateful, which is the shape `background_ema` already
established, down to the buffer discipline. It was ordered last because its
thresholds wanted the units `temporal_baseline` now provides and its output
wants somewhere to be combined; the first is settled, the second is still true —
nothing yet evaluates a two-signal rule.

**What is already paid for.** `tau_seconds` has exactly `temporal_baseline`'s
shape — a warmup that is a parameter in physical units, needing `fps` to
convert — so the contract half is done and the pattern to copy is
`TemporalBaselineParams.warmup_frames`: declare the worst case over the legal
range on the spec, override the method with the configured need.

**What it is.** The vision's "exponential decay function and a blooming touch
function", which is `a[t] = λ·(K ⊛ a[t−1]) + (1−λ)·s[t]` — the semi-implicit
Euler step of `∂a/∂t = −a/τ + D∇²a + s`. `VISION.md` step 3 category C already
names MEI and MHI, and this is them: Bobick & Davis's Motion History Image is
the same operator with a linear decay law. Name it for them so a user can find
the literature.

**Four decisions, all argued in `REFINED-VISION.md` C:**

- **Decay and coupling are one node, two parameters.** Blurring the output of a
  leaky integrator is a different operator — in the recursion the coupling
  compounds through the feedback path.
- **Physical units.** `tau_seconds`, not λ; `reach_blocks`, not κ. `fps` plumbs
  in exactly as `block_signal`'s does.
- **Two coupling modes.** `diffuse` (linear, conservative, spreads the peak
  *down* and fights the threshold) and `dilate` (grayscale morphological,
  sustains support without lowering peaks). Expect `dilate` to win; ship both.
- **Group delay is declared or removed.** A causal integrator lags its event by
  order τ, and mixing it with `windowed_mean`'s `centered` mode biases reported
  onsets late by an amount nothing writes down. Either run forward-and-backward
  for zero phase (legitimate offline) or declare the delay. Not neither.

**The stability bound is the test worth writing.** With `reach` unbounded the
dilation form propagates one detection outward at one block per frame until it
fills the arena. Run a single-block impulse through a long run and assert the
support stops growing — that is what catches a beautiful demo that is wrong.

Read: `src/sieve/filters/background_ema.py` (the twin),
`src/sieve/filters/temporal_baseline.py` (the warmup pattern),
`src/sieve/core/detection.py` (the tail this feeds), `docs/REFINED-VISION.md`
**C**, `docs/VISION.md` step 3 category C.

## Crop tools: the stamp, the drag, and the magnifier

**Gated on: nothing structurally.** This is `REFINED-VISION.md`'s **Replicates**
section read as a specification. The other half of that section — the selected
replicate being the one under tuning — landed 2026.07.27, so this inherits a tab
whose boxes are finally looked at.

**What exists.** `video_view.py` draws a new box by click-drag, selects the
topmost box under a click, and paints the set. No zoom, no pan, no handles, no
move: a drag starting on top of an existing box draws a second box over it. The
right half of `ReplicateTab` is a deliberately empty `tools_panel` waiting for
exactly this.

**The four gestures.**

- **Draw versus stamp, as a toggle.** The stamp is the labour saver: a rack is a
  dozen arenas of identical size, so the size is drawn once — or typed — and
  then placed. **Placement must preserve width and height exactly.** A stamp
  that rounds through widget coordinates and back produces twelve arenas that
  are almost the same, which is worse than one obviously different, because
  `equivalence_groups` will report them as one group while the pixels disagree.
- **Move an existing box, with `QUndoCommand.mergeWith`** so one drag collapses
  to one undo step. `commands.py`'s `SetReplicateROI` is where that goes.
- **Resize by corner and edge handles**, hit-tested *before* `_replicate_at`'s
  containment test rather than after — a handle inside another box's bounds must
  still win, or the top-left corner of a box drawn second is unreachable.
- **The magnifier, whose floor is the interesting part.** Scrolling magnifies
  but never zooms out past the natural fit, so the scale floor is `content_rect`'s
  fit scale — not 1.0, not unbounded. Every coordinate mapping in the file
  (`to_source`, `to_widget`, the paint path) currently assumes fit-scale; a
  scale factor and a pan origin have to go through all of them at once, and the
  round-trip property test in `tests/gui/test_video_view.py` is what says whether
  they did.

**Numeric entry while unlocked** is half-built: the table's X/Y/W/H columns write
through `ReplicateDocument.set_roi` and clamp. What the vision adds is the same
fields *beside the video* while a box is being placed — the same document call,
not a second edit path.

**Tests worth writing:** the zoom floor is never below fit (a wheel-out storm
leaves the frame exactly fitted, which is the invariant a naive `scale *= 0.9`
breaks); source↔widget round-trips hold under a non-fit scale with a pan offset,
extending the existing test rather than adding a parallel one; and one drag
pushes one undo command.

Read: `src/sieve/gui/{video_view,replicate_tab,commands,document}.py`,
`tests/gui/test_video_view.py`, `docs/REFINED-VISION.md` **Replicates**.

## Open, but living in the parity plan

`docs/filter-tab-parity-plan.md` has seven of its nine items landed. The two
that have not are real open work and are described there rather than restated
here:

- **Item 8 — Seeker upgrades.** Coverage as a render-event log keyed by settings
  identity, detection ticks and jumps, window bracket and Length in lockstep.
  Overlaps `docs/LATER.md` **Coverage and detection lanes on the timeline**,
  which holds the deferral reasoning; take them together.
- **Item 9 — Parity comparison finding.** Run v1 and v2 on
  `videos-testing/stab_GX010050c2_02_18_26.MP4` with matched settings and write
  the numeric agreement, the interaction latencies against the budget table, and
  a gained/lost list to `docs/findings/`. **This is the only item anywhere that
  produces evidence the rewrite did not lose signal**, which is worth weighing
  against its position in an ordering.

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
