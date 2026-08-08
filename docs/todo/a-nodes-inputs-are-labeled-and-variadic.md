---
title: The sites that predict a second input disagree — two raise, two fold the first
status: open
gated_on: nothing
priority: high
phase: "03"
opened: 2026-08-07
done_when: "uv run pytest tests/unit/test_dag.py -q -k second_upstream"
---

# The sites that predict a second input disagree — two raise, two fold the first

`Dag.node_keys` unpacks `(parent,) = fed` (`dag.py:666`) so that a second
upstream raises instead of keying on the first, and its comment says why:
"silently keying on the first of two is the failure that would otherwise be
waiting there." `executor.py:354` does the same unpack for the same reason,
uncommented. Two hundred lines above, `Dag._elements` folds `resolved[fed[0]]`
(`dag.py:455`) and `Dag._element_names` folds `elements[fed[0]]` and
`names[fed[0]]` (`dag.py:479-480`) — the silent first-of-two the comment names
as the failure being prevented. Three further sites are already variadic and
need nothing: `_edge_faults` iterates, `_source_indexed` folds with `all()`
over every parent, and `executor.py:622` takes a `min` over them.

The fold is not an oversight: 03.3 dropped v2's
`a_merge_of_two_meanings_resolves_to_neither` because no merge is expressible,
and the branch that resolved disagreeing upstreams went with the case
(`dag-is-rederived-against-schema-v1.md`, table row). What is left over is a
declared posture that holds at two sites and not at two others, in a module
where only `Pipeline`'s refusal of "two edges feed one node"
(`pipeline_model.py:715`) keeps anything from reaching the difference.

Done when `_elements` and `_element_names` refuse a second upstream the way
`node_keys` does, with a case that constructs the two-entry `upstreams` mapping
directly — `Dag.build` cannot produce one, so the case calls the static folds.
The alternative is to narrow `node_keys`' comment to a claim about itself; that
is the worse repair, because the posture is what
[adr/declared-means-verified.md](../adr/declared-means-verified.md) asks of a
declaration and two of the four sites already keep it.

## What this item is not

An earlier reading of these sites had them predicting a *pair* — a left and a
right — that the variadic concatenate-videos tool in
[VISION.md](../VISION.md)'s folder scenario would force revising. That reading
does not survive the files. `node_key`'s "this position becomes port-bound
pairs again" means the (port, key) pairs of v2's port-to-key mapping, which
`NODE_KEY_POSITIONS`' comment names four lines up as the thing `upstream`
replaced; `tool_base` predicts "a mapping of ports"; and `Dag.upstreams` says a
tuple is kept because "the day a two-input tool lands is a day this field's
shape is already right." Three of the sites already predict labeled and
variadic. What they all say is *two-input tool*, and that is the trigger event
rather than a claim about arity — a folder of videos triggers it too. Nothing
here needs the schema to grow a port field before there is a tool with ports,
which is the distinction-nothing-can-make that `Edge` refuses.

The claim that a crossing moves exactly one key still has no subject and is
still deferred on the tool that would give it one; it lives in [a merge keys
its inputs by port](a-merge-keys-its-inputs-by-port.md).
