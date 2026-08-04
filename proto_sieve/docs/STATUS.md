# Status

Where the spike is. Update this at the end of every working stretch — it is
the only thing that survives a cleared context. Read `AGENTS.md` first; this
file says only *how far*, never *what the rules are*.

Last updated: 2026-08-03 (chunk 2's live pair decided).

**The proof-first regime (red-then-green tests, `tests/`) was dropped by
Kendrick this session.** `proto_sieve/tests/` was deleted. Chunks 5 and 6
below were built and hand-verified at the REPL, not pinned by a committed
test. `AGENTS.md`'s "the proof is written before the implementation" section
is stale for everything after chunk 4 — do not treat it as still governing.

Code now lives under `proto_sieve/src/sieve/` (mirrors the real repo's
`src/sieve/` path, so a future promotion is a directory move) rather than
directly under `proto_sieve/`. Docs live under `proto_sieve/docs/`.
`proto_sieve/CLAUDE.md` stays at the top level as the pointer file.

| # | Chunk | State | Verified by |
| --- | --- | --- | --- |
| 1 | op values, recipe hash | green | test, deleted this session |
| 2 | identity — the adversarial pairs | green, **incomplete** | test, deleted this session |
| 3 | `render`, no cache | green | test, deleted this session |
| 4 | the cache, invisibly | green | test, deleted this session |
| 5 | tool declares a requirement; resolver picks the op | green | REPL check only |
| 6 | pipeline on disk | green | REPL check only |
| 7 | view as a value | green | REPL check only |
| — | GUI | not a chunk; a sitting with Kendrick, last | — |

Chunk 2's live pair — *same requirement, resolver picked a different op* — is
resolved (see `DECISIONS.md`, 2026-08-03): the resolved op enters the hash,
so `Slice` and `Resample` never collide, even when bit-identical. This was
true of the code as written (`Node.op` is the concrete resolved op, and
`_canon` tags every dataclass by type name) before it was named a decision —
naming it is what this entry records. Still unexercised by a committed test,
per the caveat below.

## Next action

All seven chunks are green and chunk 2's live pair is decided. Domain
packages under `proto_sieve/src/sieve/`, 40 tests total, all green:

- `store/` — generic name-to-file persistence (repo-root resolution,
  guarded path, text read/write/list). `pipeline/store.py` and
  `projects/registry.py` both build on it.
- `pipeline/` — `pipeline.py` (the value, JSON round-trip, lowering,
  unchanged from chunk 6) plus `store.py` (saves/loads a named pipeline to
  `proto_sieve/pipelines/<name>.json`).
- `projects/` — `Project` (name, source video path) and `registry.py`
  (`add_project`/`remove_project`/`list_projects`, persisted as one JSON
  array under `proto_sieve/config/projects.json`). Nothing is scanned;
  a project exists only because it was deliberately added — the registry
  starts empty.
- `session/` — `history.py` (undo/redo over whole `Pipeline` values),
  `session.py` (current step, draft edits, commit), `frames.py` (the frame
  for a step index), `app_state.py` (`NoProject` vs `ProjectActive`,
  `select(project)` between them).

None of the domain layer above is wired into the GUI yet. `gui/` itself
was renamed this session: `representation/` and `pipeline_panel/` are now
`canvas/` (the information side) and `control/` (the generic "user selects
stuff" space, with the pipeline step list nested at `control/pipeline/`).
That rename is deliberately not behind an enforced boundary — canvas and
control are meant to be coupled (a dragged crop box is control's current
step, drawn on the canvas), so nothing stops a canvas file importing a
control type; the one thing that stays control-only is deciding which
step or project is current. See `DECISIONS.md`.

`app.py`'s `PIPELINE` is still hardcoded and always builds the
canvas-plus-control layout; there is no project selection screen, and the
registry starts empty (no project is added automatically — see the
discovery-to-registry decision above). The planned next slice: a
`gui/control/project_select/` screen (project list on the right — where
"the left serves the right" still holds even though the import fence
doesn't — with a placeholder preview in `canvas/`, no real spec loading
yet), `app.py` branching on `AppState` instead of assuming a project, and
a one-time seed (`add_project` for the checked-in `rep3_intermittent_crop`
clip, run once, not on every launch) so the app has something to select
without requiring the add-a-project flow to exist yet. This is GUI work —
no cheap proof — done in a sitting with Kendrick.

## Caveat a fresh session must not skip

This line used to say "nothing here is committed, `proto_sieve/` is
entirely untracked" — that stopped being true partway through this
session (see recent `git log`; commits landed both from Kendrick allowing
local commits and from an auto-commit hook neither of us was watching
closely). Don't trust that sentence if you find it copied anywhere else in
these docs; `git log`/`git status` are the actual source of truth for what
survives a cleared context now, not just this file. One concrete cost of
the gap: this session's first `gui/` restructuring pass lost `rail.py`,
`step.py`, and both their `__init__.py`s (untracked, deleted by a
follow-up `rm -rf` after a failed `rmdir`) and had to be reconstructed
from the conversation transcript rather than `git checkout`. Commit early
and often in this tree from here on — the FINDINGS.md claims (chunk 4 not
forcing an edit to chunk 3, chunks 5/6/7 hashing or comparing correctly)
are still only demonstrated, not pinned by a currently-committed test,
which is a separate, still-open gap.
