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
