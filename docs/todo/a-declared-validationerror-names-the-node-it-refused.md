---
title: A declared ValidationError names the node it refused
status: done
gated_on: nothing
priority: normal
phase: "03"
done_when: "uv run pytest tests/unit/test_cache_key.py tests/unit/test_dag.py -q -k invalid_params"
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

## Both files, one keyword, and the walk's case carries the id

The cases spell `invalid_params`, one in `tests/unit/test_cache_key.py` for
`node_key` and one in `tests/unit/test_dag.py` for `node_keys`, and the
criterion names both files because a single-file run would go green with either
half written — which is the failure this item is about, a declared raise proven
on one side and inherited on the other. The walk's case is the one that has to
assert the message *contains the node id*, since that is the half pydantic does
not supply and the half the interactive loop reads; whether the id arrives by
wrapping or by re-raising is the work's to choose, and the criterion does not
name an exception type for that reason.

Not in the criterion, for the reason the paragraph above gives: nothing asserts
that the walk survives an invalid node the way it survives `NotCacheableError`.
A case pinning that would pin the behaviour this item refuses.
