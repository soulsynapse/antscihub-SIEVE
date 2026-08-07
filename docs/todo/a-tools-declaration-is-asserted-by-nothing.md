---
title: A tool's declaration is asserted by nothing
priority: high
phase: 2
status: open
gated_on: nothing
opened: 2026-08-07
---

# A tool's declaration is asserted by nothing

Both tools on the shelf declare `element`, `mode`, `version`, `primary_params`,
and `caption` in their `register_tool` call, and no test on the tree reads any
of them. Mutating each in turn on `crop` — `PRESERVED` to `AGGREGATED`,
`STREAMING` to `WINDOWED`, `primary_params` and `caption` to empty, `version`
to `2.0.0` — leaves all 276 unit tests green. `downsample` is the same shape;
only `param_stereotypes` is pinned, and only because 01.4 wrote a case for it.

Two of those five are load-bearing rather than descriptive. `element` is what
`dag.py` reads to decide an edge is legal, and `mode` is what the executor
branches on — so a tool declaring the wrong one produces a graph that validates
and runs and is wrong about what it computed, with nothing anywhere saying so.
`version` is worse in a quieter way: it is in the cache key, so a wrong value
serves another build's results.

The version worth building is not a case per field per tool, which goes stale
the moment a tool lands. It is one parameterized case over `discover()` that
asserts each spec's declarations against a table the test file holds — the
shape `test_tool_id_spelling.py` already uses for the identity values, where
adding a tool without adding its row is the failure.

`adr/declared-means-verified.md` is the rule this violates: a declaration
arrives with the thing that checks it, and these five arrived with nothing.
Filed under the tool contract's phase because that is where a reader looks for
it, but nothing gates it — `discover()` landed with 03.7.1, so the mechanism
the test would iterate is already here and every tool landing after this
inherits the gap until it is written.
