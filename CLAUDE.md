# CLAUDE.md — how to work in this repo

SIEVE is a video signal-processing tool for isolating ethological events. Its
value is the speed of the interactive tuning loop: drag a slider, watch the
graphs refill faster than the video plays. Architecture serves that or it does
not belong.

This file is the only doc loaded automatically. It routes; it does not restate.
Read the file that answers your question, not all of them.

---

## Where to look

| Question | File |
|---|---|
| What am I building, and what is the workflow supposed to feel like? | `docs/VISION.md`, then `docs/REFINED-VISION.md` |
| What are the invariants, layers, and latency budgets? | `docs/ARCHITECTURE.md` |
| Where does this module go? | `docs/SCAFFOLD.md` (machine-checked; see below) |
| What should I work on? | `docs/TODO.md` — open items only |
| Why isn't X being done yet? | `docs/LATER.md` — deferred, each with its trigger |
| Was this already built, and how? | `docs/completed-todo/.index.md` |
| What is measurably true about the system? | `docs/findings/.index.md` |
| Which guardrails actually run in CI? | `docs/AUTO-GUARDRAILS.md` |
| Why does v2 exist at all? | `docs/SIEVE-HANDOFF.md` |

There is no `src/sieve/docs/`. Interface contracts live in module docstrings —
`core/filter_base.py` is the filter contract, `core/pipeline_model.py` is the
saved artifact schema, `pipeline/cache_key.py` is key derivation — with the
reasoning in the matching `docs/completed-todo/` entry. Update the docstring
and the entry, not a separate spec file.

---

## The five non-negotiables

Full text in `docs/ARCHITECTURE.md`. A violation is a defect, not a tradeoff.

1. **Filesystem is truth at rest.** Materialized artifacts read without SIEVE
   running. During tuning, truth is in memory.
2. **Pipeline is a data structure.** Serializable DAG, no GUI-only state in it.
3. **Filter = one class + one markdown.** Discovery is automatic; nothing
   enumerates filters. Adding one must require no edit to a registry.
4. **No latency budget misses.** `src/sieve/bench/budgets.py` is the table.
5. **No regime tradeoffs.** Never improve pre-pipeline speed at in-pipeline's
   expense, or vice versa.

---

## The work loop

1. **Take one item from `docs/TODO.md`.** Items are scoped to fit one context
   window and are written so you can start without reading the whole tree.
2. **Build the checklist first**, one entry per file or gate, before the first
   edit. An item whose steps cannot be listed up front has not been read yet.
3. **Build it.** Prefer taking what exists over reinventing it — `TODO.md`'s
   *What already exists* table says what is already solved and by which module.
4. **Test the load-bearing claim, not the surface.** Two or three tests that
   would each fail for a distinct real reason. A property or benchmark earns
   its place only when it pins something an example cannot state.
5. **Run the gate**: `uv run nox -s checks`. It must pass.
6. **Complete atomically.** Delete the item's section from `TODO.md` and write
   `docs/completed-todo/YYYY.MM.DD-name.md` from that folder's `_TEMPLATE.md`.
   Never mark an item done in place — a finished item is *moved*.
7. **Measurements go to `docs/findings/`**, never into the completed entry. A
   completed entry says what was built; a finding says what is true about the
   system and outlives the code that prompted it.
8. **Rebuild the indexes**: `uv run nox -s docs`. Staleness is a test failure.
9. **Commit, then push.** Commits do not count until pushed.

Work that is real but not yet timely goes to `docs/LATER.md` with the trigger
that would make it takeable — not into `TODO.md` to grow stale.

---

## Gates

```
uv run nox -s checks      # ruff + ruff format + pyright strict + import-linter + pytest
uv run nox -s benchmark   # timed budget checks (marker-selected)
uv run nox -s docs        # regenerate docs/*/.index.md
```

`checks` is the default session and is exactly what CI runs
(`.github/workflows/ci.yml` runs `nox -s checks benchmark`). Everything is
`uv run`-prefixed; sessions reuse the synced `.venv` rather than building their
own.

---

## Placement

**New filter** — `src/sieve/filters/<name>.py` (spec + `@kernel` per backend)
plus `src/sieve/filters/<name>.md` beside it. Nothing else. A test fails if the
markdown is missing or if `filters/__init__.py` names any filter module.

**New module** — check `docs/SCAFFOLD.md`. It is split into a *current* tree and
a *projected, not built* section, and `tests/docs/test_scaffold.py` asserts
those two claims stay true. If you add a module, add it to the current tree; if
you build something the projected section named, move the line.

**New test** — by kind:

| Kind | Directory | Note |
|---|---|---|
| Pure logic, one module | `tests/unit/` | |
| Hypothesis property | `tests/property/` | deadline already disabled by conftest |
| CLI / decode end-to-end | `tests/integration/` | |
| Qt | `tests/gui/` | **must** set `pytestmark = pytest.mark.gui` at module level |
| Timing budget | `tests/bench/` | `pytestmark = [pytest.mark.gui, pytest.mark.benchmark]` |

`tests/conftest.py` gives a session-scoped `synthetic_video`: 40 frames, 20 fps,
160x120, where frame `n` has blue channel `n * 5` — so a test can assert *which*
frame a seek landed on, not merely that something decoded.

---

## Things that cost a cycle if you don't know them

- **pyright runs in `strict` mode with a no-ignores rule.** Fix the type, do not
  suppress it.
- **`pytestmark` is only read from test modules and classes.** A `gui` marker in
  a conftest is silently inert. Every Qt test module declares its own.
- **Markers are `--strict-markers`.** Only `slow`, `gui`, `cuda`, and
  pytest-benchmark's own `benchmark` exist.
- **`.importlinter` is the machine-checked layer contract**, and it declares
  layers that do not exist yet in parentheses so the contract governs them from
  their first commit. `sieve.filters` is deliberately *allowed* to import `cv2`;
  `core`, `bench`, `gui`, and `cli` are not.
- **`docs/*/.index.md` are generated** by `tools/doc_index.py`. Do not hand-edit;
  frontmatter keys are required and a missing one raises rather than rendering
  blank.
- **Platform is Windows.** The shell is PowerShell by default; a Bash tool is
  also available. Paths in docs use whichever the surrounding file uses.

---

## Style of the docs themselves

These docs are written as argument, not as changelog: they say *why* a thing is
the way it is, and they record the decision that was rejected alongside the one
that was taken. Two rules keep that from turning into accretion:

- **One home per fact.** History belongs in `docs/completed-todo/`, measurements
  in `docs/findings/`, deferrals in `docs/LATER.md`, open work in `docs/TODO.md`.
  If you are about to restate in one what another already holds, link instead.
- **A doc that asserts a fact about the code should be checkable.** Prefer a
  table a test can parse over a paragraph a reader must trust. The budget table,
  the doc indexes, and the scaffold tree are all machine-checked for this reason;
  that is the mechanism that kept them true while the prose around them drifted.
