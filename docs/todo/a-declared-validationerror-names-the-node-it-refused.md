---
title: A declared ValidationError names the node it refused
status: open
gated_on: nothing
priority: normal
phase: "03"
opened: 2026-08-07
---

# A declared ValidationError names the node it refused

`cache_key.node_key` and `Dag.node_keys` both declare `Raises: ValidationError`
and nothing proves either one — the name is not imported in either module and
no test asserts it. `test_dag.py`'s own `TestLookups` states the standard this
falls short of: a declared raise nothing proves is a sentence in a docstring
rather than a contract. It is reachable, not decorative — `spec.params_model.
model_validate` is the last statement before the digest, so a document that
`Dag.build` accepted (build checks edges and elements, not parameter values)
first fails here.

Two things have to land together. The raise needs a test, in `test_cache_key.py`
for the single node and in `test_dag.py` for the walk. And the walk's version
has to name the node: pydantic's message carries the field and the model but
not the `node_id`, and this fires mid-traversal in the interactive loop, where
"radius must be odd" without a node is a hunt through the graph. Wrapping or
re-raising with the id is the fix; which of the two is the decision.

Deliberately not in scope: making the walk survive it the way it survives
`NotCacheableError`. Uncacheable is a property of a tool and not an error;
invalid parameters are a document that cannot run at all, and swallowing them
per node would hand the executor a graph it will fail on later and further away.
