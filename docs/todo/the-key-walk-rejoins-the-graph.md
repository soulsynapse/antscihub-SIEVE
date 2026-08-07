---
title: The key walk rejoins the graph
step: "03.4.1"
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_dag.py -q -k KeyWalk"
opened: 2026-08-07
---

# The key walk rejoins the graph

`Dag.node_keys` — one pass in topological order handing each node its
upstreams' keys, so `cache_key.py` can compute one node's key and decline to
say which nodes those are. 03.3 could not carry it: the walk's body is two
calls into `pipeline/cache_key.py`, which 03.4 is the step that writes.

It runs before 03.5 and 03.6 because both consume it — the plan asks which
nodes are already cached and the executor writes under the key — and it is a
step of its own rather than an edit to 03.4's item because a criterion may not
be widened after the fact.

Three v2 cases were dropped from 03.3's table with this as the reason, and each
is a claim that has to land here rather than be reinvented:
`the_walk_is_the_hand_walk` (the traversal produces exactly what a hand walk
through `node_key` produces, which is what stops the graph growing a second
idea of what a key is), `an_uncacheable_node_takes_its_descendants_and_nobody_else`
(`NotCacheableError` is swallowed at the node that raises it and propagates by
absence, so one non-deterministic node in a twelve-node graph does not cost the
other eleven their cache entries), and
`swapping_a_merges_ports_moves_its_key_and_only_its_key`, whose subject is a
merge and stays dropped until a two-input tool exists.

v2's signature carried `backend` and `lowered_prefix`. The first is gone
(`adr/no-kernel-apparatus.md`). The second names a type `decode/lowered.py`
does hold, but the lowering that produces one is `pipeline/lowering.py`, which
PLAN.md does not build until a budget is missed — so the parameter arrives with
its producer and not before.
