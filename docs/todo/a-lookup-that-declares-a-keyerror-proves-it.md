---
title: A lookup that declares a KeyError proves it
priority: low
phase: 0
status: open
gated_on: nothing
opened: 2026-08-07
---

# A lookup that declares a KeyError proves it

`Pipeline.node` and `Project.replicate` each end in `raise KeyError(...)` under a
docstring `Raises:` section, and each survives being replaced with `pass` while
`tests/unit/test_pipeline_model.py` and `tests/unit/test_replicates.py` stay
green — the only two of the module's 24 `raise` statements that do
(`findings/loop/2026.08.07-a-mutation-sweep-enumerated-by-hand-misses-what-it-did-not-look-for.md`).
Neutered, both return `None` instead of raising, so a caller that looked up a
node that is not there gets an `AttributeError` several frames later rather than
a `KeyError` naming the id it asked for.

Nothing depends on it yet, which is why this is a pool item and not a decimal
step. The first caller is `02.2`'s DAG, which resolves edge endpoints through
`Pipeline.node`; a case per lookup asserting `pytest.raises(KeyError)` on an
absent id is the whole of it. Doing it when the DAG lands means the declaration
and its first consumer are proven in the same commit.
