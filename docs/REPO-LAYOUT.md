# Repo layout and boundary rules

Python 3.11. The tree mirrors the layers in [ARCHITECTURE.md](ARCHITECTURE.md) exactly, so
that "where does this go" is answerable without reading any code.

```
sieve/
  kernel/
    types.py          closed vocabulary of intermediate types
    intents.py        intent shapes + parameter normalization
    registry.py       provider registration and lookup
    providers/        one module per provider family; span providers live here too
  executor/
    plan.py           resolve(request) -> Plan: lowering, cover selection, materialization
    cover.py          min-cost cover over the intent DAG
    cost.py           measured cost lookup
    realize.py        realize(plan, scope) -> Result
    cache.py          content-addressed intermediate + artifact cache
  equivalence/
    signature.py      compute, store, compare signatures
    probes.py         built-in probes; user probe registration
    stats.py          TOST and bootstrap equivalence tests
    registry.py       equivalence records; substitution admissibility
    references/       reference set manifest (media by hash, not in-tree)
  pipeline/
    model.py          Pipeline, StepNode, ports, offers, bindings, overrides
    expand.py         program -> instances
    validate.py       ready | blocked(reasons)
    io.py             load/save
    migrations/       migrate_<n>_to_<n+1>, one per major bump
  steps/
    crop/             spec.py, panel.py, offers.py
    downsample/
  gui/
    shell.py          two-panel shell, keyboard navigation
    viewers/          project viewer, video surface, overlay layers
    panels.py         host for step-owned config panels
  prefs/
  cli/
tests/
  conformance/        per-contract suites parameterized over all implementers
  equivalence/        signature and regression checks
  unit/
docs/
ratchets.toml
```

## Import rules

Dependencies point in one direction only:

```
kernel  ←  executor  ←  steps  ←  pipeline  ←  gui
                            equivalence  →  kernel
```

- `kernel` imports nothing from SIEVE.
- `executor` imports `kernel` and `equivalence`.
- `steps` import `executor` types and `pipeline` types. Never `kernel`, never `gui`.
- `gui` imports `pipeline` and `steps`. Never `executor`, never `kernel`.
- `equivalence` imports `kernel` only.

Enforced by an import-linter contract in CI, not by review. A violation is a design error,
not a style error: a step importing the kernel is the exact move that produces the
unmaintainable version of this program.

## Where things go

New compute → `kernel/providers/`. New fast path → also `kernel/providers/`, as a span
provider, plus an equivalence record. New user-facing capability → `steps/<name>/`. New
thing to draw on the video → `gui/viewers/` as a general overlay layer, plus a declaration
in the step that wants it. Anything that "needs to know about both a step and the kernel"
is a design error; find the intent that both sides should have been speaking through.

## Naming

`kind` strings for steps and `name` strings for providers appear in saved files and in
signature keys, so renaming either is a contract change with a migration. Pick them
carefully once. Internal class and module names are free.
