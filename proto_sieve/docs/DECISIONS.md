# Decisions

One line each, made in passing, never argued into a document. This file exists
so that a decision does not become a drafting session.

Format: `<date> — <decision> — <why, in a clause>`

- 2026-08-03 — the harness splits in two: a **measurement** harness that
  produces an interchangeability table (offline, statistical, corpus-driven)
  and a **resolver** that consumes it (hot path, deterministic, no
  measurement) — because a runtime path must not depend on a statistical
  instrument, and the table is a value that can be stale without being
  wrong-in-kind. Only the resolver is in this spike.
- 2026-08-03 — a tool **declares a requirement**; it does not construct a
  graph of named ops — because implementation choice belongs to the resolver,
  which is what lets ops be free and autopopulated by dispatch. This differs
  from `Tool.lower(p)` as written in the repo, deliberately.
- 2026-08-03 — the pipeline is a DAG, and the GUI's up/down arrows walk a
  **spanning tree** over it, not the graph — so "down" from a branch is a
  choice the GUI makes, not a fact the pipeline holds.
- 2026-08-03 — "ops are free" means free to *write* (proliferation is fine,
  dispatch finds them). It is not a claim about run cost; only the resolver
  reasons about that.
- 2026-08-03 — the recipe hash carries a scheme version from the first commit
  — one field now converts an unrecoverable decision into a recoverable one.
- 2026-08-03 — **open, and the most expensive thing here**: does the resolved
  op enter the recipe hash? If it does not, two computations share one address
  and the store serves whichever landed first. Chunk 2 states the pair; it is
  not answered by writing the hash function.
- 2026-08-03 — the proof-first regime is dropped for chunks 5 onward; `tests/`
  is deleted — Kendrick chose to move on plain implementation instead. See
  `STATUS.md` for what that costs (chunks 5/6 are REPL-verified, not pinned).
- 2026-08-03 — code moved from `proto_sieve/*.py` to `proto_sieve/src/sieve/*.py`,
  docs moved to `proto_sieve/docs/` — mirrors the real repo's `src/sieve/`
  path so a later promotion is a directory move, not a rewrite. Nothing was
  copied from the real `src/sieve/`; the two trees still do not import each
  other.
- 2026-08-03 — chunk 2's live pair resolved: the resolved op enters the hash,
  so `Slice` and `Resample` never collide even when bit-identical — collision
  would smuggle the deferred interchangeability claim into the resolver's hot
  path; no-collision-to-collision is additive later, the reverse isn't.
- 2026-08-03 — tests live in a `__tests__/` directory colocated with the
  modules they cover (`sieve/__tests__/test_kernel.py` next to `sieve/kernel.py`,
  `sieve/tools/__tests__/test_crop.py` next to `sieve/tools/crop.py` — one
  `__tests__/` per directory of modules, not a top-level `tests/` tree) — a
  module that can't test its own claim isn't the one that owns that claim.
- 2026-08-03 — `_fence/` (a shared checker plus a completeness test forcing
  every directory to own a fence test) is deleted; gui's fence test goes back
  to a standalone inline scan — one directory's claim doesn't need a shared
  module or a tree-wide completeness rule to back it, and both were reaching
  for generality this spike isn't asking for yet.
- 2026-08-03 — a new `session/` package holds GUI-facing app state (current
  pipeline, current step, undo/redo), separate from `pipeline.py`'s on-disk
  value and separate from the measurement `harness` named above — that word
  stays reserved for the interchangeability table so the two are never
  confused. `session/history.py` (first module) tracks whole committed
  `Pipeline` values on two stacks, not diffs or commands — undo/redo is
  moving a pointer through values, which is what a small immutable value
  makes cheap; a command-pattern undo would be solving a problem this
  spike doesn't have yet.
- 2026-08-03 — `session/` built out: `history.py` (undo/redo over whole
  `Pipeline` values), `session.py` (current index plus at most one draft —
  an uncommitted `Step` replacement, not part of the pipeline value until
  `commit`), `frames.py` (frame for a step index — truncate `steps[:n+1]`,
  lower, render; `-1` means the bound source, untouched). `frames.py` keeps
  no cache of its own: two truncations sharing a prefix hash to the same
  `Node`s, so `executor`'s existing cache already makes stepping and
  undo/redo reuse work for free — confirmed by
  `test_stepping_reuses_the_executors_cache_for_the_shared_prefix`. 13
  tests, colocated in `session/__tests__/`.
- 2026-08-03 — `pipeline.py` became a `pipeline/` package: `pipeline.py`
  keeps chunk 6's secret (the value, JSON round-trip, lowering) unchanged;
  a new `store.py` owns a separate secret — how a *name* resolves to a file
  (`<dir>/<name>.json`, default `proto_sieve/pipelines/`) — because "what a
  pipeline is" and "where a saved one lives" are different claims with
  different proofs. `__init__.py` re-exports both so the ten existing
  `from ...pipeline import Pipeline, Step, lower` sites needed no changes.
  5 new tests (`test_pipeline.py`, `test_store.py`) pin the round-trip,
  the lowering-hash claim, and that a name can't escape the directory
  (`../x`, `a/b`) — the last one wasn't asked for, added because `store.py`
  is the first module in this spike that turns a string into a path.
- 2026-08-03 — a new `store/` package (sibling to `pipeline/`, `session/`)
  owns the generic secret `pipeline/store.py` was about to duplicate a
  second time for projects: repo-root resolution, name-to-guarded-path,
  read/write/list text under a directory. `pipeline/store.py` now builds on
  it (thinner — its own secret is just "which directory, and Pipeline↔JSON
  via to_json/from_json"), and `projects/discovery.py` reuses `repo_root()`
  for the default video directory but keeps its own scan (extension glob,
  not a name-guarded write) since discovering existing files and writing a
  named one are different operations.
- 2026-08-03 — a new `projects/` package (sibling to `pipeline/`, `store/`):
  `projects.py` holds the `Project` value (name, source path — name matches
  the convention `Pipeline.source` uses); `discovery.py` lists one project
  per video file under `video-test/`. One real video exists today, so
  discovery returns a list of one — not faked to look like more.
- 2026-08-03 — `session/app_state.py`: `NoProject` vs `ProjectActive`
  (project plus a live `Session`), `select(project)` the only path between
  them, seeding an empty `Pipeline(source=project.name)` — which saved
  pipeline (if any) should load by default on selection is still open.
  Deliberately not part of `session.py` — "is a project chosen yet" is a
  different, earlier secret than "editing a given pipeline."
  16 new tests across `store/`, `projects/`, `session/__tests__/test_app_state.py`;
  40 total in `proto_sieve/src/sieve`, all green.
- 2026-08-03 — projects are never discovered by scanning `video-test/` —
  `discovery.py` deleted, replaced by `registry.py`: a project exists only
  because `add_project` was called, persisted as one JSON array (one file,
  `proto_sieve/config/projects.json` by default) through `store/`'s
  name-to-file primitive. Kendrick's correction: scanning a directory was
  standing in for a decision — which projects the app knows about — that
  belongs to the user, not to what files happen to sit in a folder.
- 2026-08-03 — `gui/representation/` and `gui/pipeline_panel/` renamed to
  `gui/canvas/` and `gui/control/` (`pipeline/` nested one level inside
  `control/` so a second control, project selection, can sit alongside it).
  Canvas is the information side, control is the generic "user selects
  stuff" space; the only thing that stays control's alone is deciding
  which step or project is *current* — a canvas reacts to that, it never
  sets it. Everything else about the two is deliberately unenforced:
  Kendrick's call is that canvas and control are genuinely coupled, a
  canvas is in effect an extension of whichever control is active (a
  dragged crop box is control's current step, drawn somewhere else), so an
  import-direction fence between the packages would be encoding a
  separation the design doesn't actually want. No fence test for this one.
  Recovery note: the move's first attempt lost `rail.py`/`step.py` and both
  their `__init__.py`s — never committed to git (only `pipeline.py` itself
  was, in an earlier commit), deleted by an `rm -rf` that ran after a failed
  `rmdir` broke the intended move. Reconstructed from this session's own
  transcript, not from disk or git.
- 2026-08-03 — the step-halo backdrop (`style.ROLE_STEP_HALO`, the wrapper
  widget behind the current tick) is temporarily unwired in `rail.py` — it
  was blocking launches. Root cause not diagnosed; `rail.py` now tags the
  current tick's color directly (`ROLE_STEP_TICK_CURRENT`) with no wrapper
  widget. `style.py`'s role constant and QSS rule are left in place,
  unused, so re-wiring later is a `rail.py`-only change.
- 2026-08-03 — `gui/control/project_select/`: `ProjectSelect` lists the
  registry's projects and emits `project_selected` (a `Project`) when one
  is clicked; an "Add project…" button opens a file picker, names the
  project from the video file's stem, and calls `projects.add_project`
  directly — same pattern as `windows/preferences.py`'s accent picker
  calling `appearance_prefs.set_appearance` directly, a control can act on
  a domain mutation without a caller mediating it. This module never
  touches `AppState`; it only emits which project was picked. Not wired
  into `app.py` yet — `app.py` branching on `AppState` (this screen when
  `NoProject`, the existing canvas+pipeline layout when `ProjectActive`)
  is still the open item before the GUI sitting.
- 2026-08-03 — the rest of the step-tick role tagging (`ROLE_STEP_TICK`,
  `ROLE_STEP_TICK_CURRENT`) is also temporarily unwired — still blocking
  launches after the halo alone was disabled. `rail.py` renders every tick
  as a plain unstyled `QWidget`; `current` is still tracked and passed
  through but has no visible effect. Root cause not diagnosed for either
  this or the halo — `style.py`'s role constants and QSS rules are
  untouched, so re-wiring is confined to `rail.py` once whatever's wrong
  with the `role` property/QSS selectors here is found.
- 2026-08-03 — `store.py`'s docstring tightened: it claimed content-encoding
  indifference while every call site relied on the `suffix=".json"`
  default without ever overriding it, so the genericity was aspirational,
  unexercised. Docstring now says the default is a convenience, not an
  assumption; added `test_suffix_is_not_hardcoded_to_json` (`.txt`,
  round-trips, `list_names` respects it too) so the claim is actually
  pinned rather than just stated. Behavior unchanged.
- 2026-08-03 — `app.py` wired to the real project layer: `MainWindow`
  starts in `app_state.NoProject`, central widget is
  `compose(top, <placeholder label>, ProjectSelect(list_projects()), bottom)`.
  Picking a project calls `app_state.select`, then rebuilds the central
  widget as `compose(top, VideoPlayer, PipelinePanel, bottom)` against the
  fresh empty pipeline `select` seeds and the project's `source_path`. The
  hardcoded `PIPELINE`/`VIDEO_PATH` constants are gone. The left slot in
  the no-project screen is a bare `QLabel`, not a real canvas
  implementation — still nothing designed there, per
  `gui/canvas/__init__.py`'s "a project preview" gap. No save/load of a
  chosen pipeline yet — every selection starts empty, per `app_state.py`'s
  still-open question. Smoke-launched (`MainWindow` shown, closed via a
  timer) rather than proven by a committed GUI test — this is the GUI
  sitting's territory, no cheap proof.
- 2026-08-03 — the breadcrumb-bar collapse (`6bbb9d1`) is reverted
  (`c4ba472`); animated sliding is back, but as one three-position track
  (project info, Pipeline, Step), not the old two nested two-position ones.
  `gui/control/control.py` (new) owns the track, the rail, and
  `current_position()` — dissolving `PipelinePanel`, whose Pipeline/Step
  distinction was the only reason `control/pipeline/pipeline.py` existed as
  more than a step-list builder. That file is kept anyway, slimmed to just
  `build_step_list` — Kendrick's call, over dissolving `pipeline/` into
  `rail/`/`step/` siblings of `control.py`, so the package boundary stays
  put even though the name now undersells what's left in it.
  `layout.CanvasSlot` is back too (canvas swapped in place, no rebuild),
  but `app.py` no longer owns pane/rail construction at all — that's
  `control.py`'s now, keeping `app.py` to `AppState` transitions and
  canvas/control coordination, per Kendrick's "not a dumping ground."
  The rail's `current_index` is `session.Session.current_index`, passed in
  by `app.py` on every `show_workspace` call rather than hardcoded to 0 —
  the one domain fact this pass was still faking. Which *pane* (Pipeline
  vs Step) is showing has no `Session` equivalent and stays `control.py`'s
  own secret; `Session` stays headless, no Qt. 44 tests still green.
- 2026-08-03 — the sliding track animates in *pane units*, not pixels.
  `_SlidingPanes` animates a float `offset` property (1.5 = halfway between
  panes 1 and 2) and derives the track's pixel position from it, so a
  resize mid-slide re-lays out at the fraction reached instead of having to
  stop the animation and jump (which is what the pixel version did from
  `resizeEvent`). That mattered because every transition in or out of the
  workspace resizes the track — `Control` shows or hides the rail beside it
  — so Pipeline <-> Step were the only transitions that ever animated.
  The rail now keeps its width when hidden (`setRetainSizeWhenHidden`) and
  is a fixed one tick wide whatever the step count, so no navigation
  changes the track's width at all. Same pass: `Control`'s layout spacing
  goes to 0 and its right margin to the rail's width, so the panes sit in
  equal whitespace either side instead of inset 14px left, 0 right.
- 2026-08-03 — the GUI is chunk 8, not an exemption. `AGENTS.md` used to say
  "the GUI is not a chunk. It has no cheap proof" — one clause justifying the
  other, but dropping it out of the table took its *fence* away too, and a
  halt or a co-touch is declared against a fence, not against a proof. So GUI
  sittings could not produce a finding at all, which is the only thing this
  spike is for. It now has a table row with `none` in the proof column and a
  fence named at the start of each sitting. Nothing else changes: no test, no
  apparatus, the sitting-with-Kendrick rule stands. Two findings that were
  already owed under the corrected rule are backfilled into `FINDINGS.md`
  (the missing "slide finished" signal on `Control`; the twelve-file repo-root
  walk). Still unaddressed and deliberately not folded in: `STATUS.md`'s
  dropping of the proof-first regime after chunk 4 left finding list 1 with no
  mechanism anywhere in the tree, GUI or otherwise.
- 2026-08-03 — **a tool registry exists and it lives in `pipeline/pipeline.py`**
  (`_TOOLS = {"crop": (Crop, CropParams)}`, plus a concrete import of
  `tools.crop` and an exported `tool_for` nothing calls) — recorded because
  `AGENTS.md` lists "the registry" under *Deliberately absent*, so this is a
  deferred decision that got made in passing, in a neighbour's file, and never
  declared. Left where it is for now; the point is that it stops being
  invisible. What it costs: `pipeline/pipeline.py`'s stated secret is what a
  pipeline *value* is, and adding a second tool edits it. The name-to-class
  mapping is `tools/`'s fact — `tools/` does not yet have an `__init__.py` to
  put it in, which is the same observation from the other side.
