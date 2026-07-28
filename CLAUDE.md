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
| What is the state of play right now, in one read? | `docs/.state.md` — generated; read it before TODO.md |
| What am I building, and what is the workflow supposed to feel like? | `docs/VISION.md`, then `docs/REFINED-VISION.md` |
| What is this ultimately for, and is my item walking toward it? | `docs/ASPIRATIONS.md` — A1–A3 and the invariants; derivation in `docs/WORKING-BACKWARDS.md` |
| What are the invariants, layers, and latency budgets? | `docs/ARCHITECTURE.md` |
| Where does this module go? | `docs/SCAFFOLD.md` (machine-checked; see below) |
| What should I work on? | `docs/todo/` — one file per item, `status: open` |
| Why isn't X being done yet? | `docs/todo/` — `status: deferred`, trigger in `gated_on` |
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

## The eight rules

Full text in `docs/ARCHITECTURE.md`. A violation is a defect, not a tradeoff.
Older docstrings call these "non-negotiable #N"; the numbers still hold.
Each rule there now states the **objective** it serves (O1–O4, defined at the
top of that document) and its **falsifier** — the pre-stated condition under
which revising the rule, not obeying it, is correct. Revision through the
falsifier is the legitimate path; obeying a rule into absurdity is a defect
too. Budgets are scoped to the reference workload and can carry declared
debt (`bench/budgets.py` `IN_DEBT`) — see rule 4's section there.

1. **One execution path.** `pipeline/executor.execute` is the only thing that
   computes a frame. The GUI is a view over it, never a second implementation.
2. **Pipeline is a data structure.** Serializable DAG, no GUI-only state in it —
   and the complete input to rule 1's one path.
3. **Filter = one module + one markdown.** Discovery is automatic; nothing
   enumerates filters. Adding one must require no edit to a registry.
4. **Every budget has a producer, and a miss is visible.**
   `src/sieve/bench/budgets.py` is the table; `WITHOUT_PRODUCER` is the honest
   gap in it. A ceiling nothing publishes is a number, not a budget.
5. **No consumer starves another.** Every path that can take more than one core,
   or a bounded slab of memory, declares its share in `gui/concurrency.py`.
6. **A result must never look better-founded than it is.** Refuse rather than
   approximate. Absent must not render as zero; unexamined must not render as
   quiet. Mirror direction: a control must never look more live than it is —
   faded must mean frozen.
7. **Everything sits on one side of the identity line.** A field changes *what
   a result is* (hashed) or only *where it lives and how fast it arrives*
   (never hashed). Nothing straddles; `checkpoints` and `outputs` live on
   `Project`, off `Node`, for this reason.
8. **Filesystem is truth at rest.** What SIEVE writes reads back without SIEVE
   running, and a writer proves it by reading its own output back before
   registering it. An artifact that fails verification is deleted, never
   recorded. This was rule 1, was demoted to a commitment because nothing had
   ever been at rest, and returned to the table 2026-07-28 with the replicate
   crop writer (`pipeline/materialize.py`).

---

## The work loop

1. **Take one `status: open` item from `docs/todo/`** (`docs/.state.md` lists
   them). Items are scoped to fit one context window and are written so you
   can start without reading the whole tree.
2. **Build the checklist first**, one entry per file or gate, before the first
   edit. An item whose steps cannot be listed up front has not been read yet.
3. **Build it.** Prefer taking what exists over reinventing it — `TODO.md`'s
   *What already exists* table says what is already solved and by which module.
4. **Test the load-bearing claim, not the surface.** Two or three tests that
   would each fail for a distinct real reason. A property or benchmark earns
   its place only when it pins something an example cannot state.
5. **Run the gate**: `uv run nox -s checks`. It must pass.
6. **Complete atomically.** `uv run python tools/complete_item.py <slug>`
   *moves* the item file to `docs/completed-todo/YYYY.MM.DD-<slug>.md` with
   the completion frontmatter and git-derived file lists scaffolded and the
   item body preserved for trimming. Never mark an item done in place — a
   finished item is *moved*.
7. **Measurements go to `docs/findings/`**, never into the completed entry. A
   completed entry says what was built; a finding says what is true about the
   system and outlives the code that prompted it.
8. **Rebuild the indexes**: `uv run nox -s docs`. Staleness is a test failure.
9. **Commit, then push.** Commits do not count until pushed.

Work that is real but not yet timely is a `docs/todo/` file with
`status: deferred` and its trigger in `gated_on` — promotion is a one-line
`status:` flip when the trigger fires, not a rewrite.

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
  in `docs/findings/`, open and deferred work in `docs/todo/`. If you are about
  to restate in one what another already holds, link instead.
- **A doc that asserts a fact about the code should be checkable.** Prefer a
  table a test can parse over a paragraph a reader must trust. The budget table,
  the doc indexes, and the scaffold tree are all machine-checked for this reason;
  that is the mechanism that kept them true while the prose around them drifted.
- **Only two things bind: the seven rules and what CI checks.** Everything else
  is evidence — findings can be superseded, records age without being wrong,
  and a doc you disagree with is an argument to answer, not a law to obey. The
  v1 doc tree died of the opposite: nineteen ADRs prescribing an architecture
  before the code existed, each one a standing constraint. Prose that claims
  current truth carries a `reviewed:`/`subjects:` stamp and `tools/doc_drift.py`
  *reports* (never gates) when its subjects moved; VISION, REFINED-VISION,
  SIEVE-HANDOFF, and the parity plan are dated records — superseded, never
  edited.
