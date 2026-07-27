# SIEVE rewrite — why v2 exists

This is the framing document. `CLAUDE.md` at the repo root is the operational
one: where things live, what the gates are, how the work loop runs. Read that
first; read this when you want to know why the constraints are shaped the way
they are.

## What happened to v1

A v1 exists in a separate folder (`antscihub-optical-flow-detector`). You may
check against it when necessary, but should not without reason. It shipped and
served its purpose, then became difficult to maintain — the kind of drift that
happens when structure is not enforced by tooling. The rewrite exists so that
structure enforces itself.

That is not an abstract goal. The distance between a clean codebase and an
unmaintainable one is short and mostly invisible until you are already down it,
which is why the answer is not discipline but instrumentation: build the checks
that make drift visible early, then trust them and move fast. The point of a
guardrail is precisely that you stop holding the constraint in your head.

`docs/AUTO-GUARDRAILS.md` is the current set, each with the artifact that
enforces it and an honest note on how much is covered. Build new ones as needed;
a guardrail earns its place when it converts a class of mistake into a test
failure.

## What matters, in order

**Speed of the interactive tuning loop.** Users do not fall in love with an
architecture. They fall in love with dragging a slider and watching graphs fill
in faster than the video plays. The latency budgets in `docs/ARCHITECTURE.md`
are the operational definition of that — they approximate product requirements,
not aspirations, which is why a miss is non-negotiable #4 rather than a known
issue.

**Staying editable as it grows.** v1 did not. Every structural choice here — one
execution path, the pipeline as data, a filter being one class and one markdown —
is downstream of that, and each is machine-checked because a rule that is only
reviewed is a rule that erodes.

## Where the interface contracts live

An earlier version of this file directed the agent to update eight specification
documents in `src\sieve\docs\` — `FILTER_CONTRACT.md`, `PIPELINE_SCHEMA.md`,
`CACHE_KEY_SPEC.md`, and five more. **That directory never existed and none of
those files were ever written.** The instruction sat here for two weeks sending
every reader down a dead path, which is a fair illustration of the drift this
document is about.

What actually happened is better than what was planned: the contracts live in
the module docstrings of the code that implements them, with the reasoning in the
matching `docs/completed-todo/` entry. A contract cannot drift from an
implementation it is written inside.

| Intended spec | Actual home |
|---|---|
| Filter contract | `core/filter_base.py` + `completed-todo/2026.07.25-filter-contract*.md` |
| Pipeline schema | `core/pipeline_model.py` + `completed-todo/2026.07.25-pipeline-artifact.md` |
| Cache key derivation | `pipeline/cache_key.py` + `completed-todo/2026.07.25-cache-key.md` |
| Backend dispatch | `backend/dispatch.py` + `completed-todo/2026.07.25-per-node-backend.md` |
| Preview semantics | `pipeline/preview.py`, `core.source_warmup_frames` + `completed-todo/2026.07.26-the-representative-clip-preview.md` |
| Guidance format | the convention in `filters/__init__.py`, enforced by `tests/unit/test_filter_discovery.py` |
| Worker protocol | nowhere — `workers/` does not exist; see `docs/LATER.md` *Process isolation* |
| Review output | nowhere — `review/` does not exist; see `docs/LATER.md` *HPC handoff, and review mode* |

So: when you change one of these, update the docstring and the completed-todo
entry. Do not create a spec file for it.

## Starting work

You were probably told to build one thing. If something else needs to exist
first, or be fixed first, or is in conflict — and you are at least 95% sure what
is wanted — just do it.

`docs/ARCHITECTURE.md` says how it fits. `docs/SCAFFOLD.md` says where it goes,
and is machine-checked in both directions, so a module it names under **Built**
exists and a module it names under **Projected** does not. Treat it as
authoritative; that was not true of its predecessor, which named a napari viewer
and a visual DAG editor for two weeks after both were rejected.
