---
title: The window grows a port-keyed form, and the executor delays each port to the slowest
step: "11.2"
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_executor.py tests/unit/test_cache_key.py -q -k 'two_parents_of_different_lag_align_at_the_child or swapping_two_ports_moves_one_key'"
opened: 2026-08-09
---

# The window grows a port-keyed form, and the executor delays each port

The contract half is anticipated rather than open: VISION says two inputs into
one step "lands as the contract-plus-executor extension ADR-2 anticipated —
`window` grows a port-keyed form — not as something a tool improvises", and
[a-nodes-inputs-are-labeled-and-variadic.md](a-nodes-inputs-are-labeled-and-variadic.md)
already settled that an edge carries a port label and a node's inputs are an
ordered mapping of them. What is not written anywhere is the price, and it is
two things, neither of which is a signature change.

**The executor's no-alignment invariant breaks.** Today every node has one
parent, so `emitted[parent]` is the frame the child wants and the `max()` over
parent lags is a formality. Two parents of different lag hand a node frames of
different index at the same step, so each port needs a delay buffer of
`max_lag - lag[port]` and the loop grows a holding stage it does not have. This
is machinery inside the one execution loop, which is the layer
[adr/one-execution-path.md](../adr/one-execution-path.md) makes expensive to get
wrong: preview and production share it, so a misaligned merge is wrong in both
and wrong identically, which is the one failure mode parity testing cannot see.

**The node key's `upstream` slot becomes ordered pairs.** One value becomes
`(port, key)` pairs in order, which moves the digest for every node with a
parent — a `HASH_VERSION` bump, and the whole store turns over. That is the
first schema-shaped bump this repo makes and 11.1 is the rule it runs under.

The second `-k` term is
[a-merge-keys-its-inputs-by-port.md](a-merge-keys-its-inputs-by-port.md)'s own
claim, deferred since 2026-08-07 for want of a subject: crossing two inputs over
moves exactly one key and leaves every other standing. That item's 2026-08-09
ruling says the gate is prose and invisible to the index scan, so the citation
here is the whole net — but the tool that gives it a runnable subject is 11.3,
and what this step owes is the key layout the crossing moves. Whether the case
lands here or there is 11.3's to settle; the deferral lifts once one of them
runs it.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/unit/test_executor.py tests/unit/test_cache_key.py -q -k 'two_parents_of_different_lag_align_at_the_child or swapping_two_ports_moves_one_key'
    35 deselected in 0.16s
    exit: 5

## Folded 2026-08-10: the price is three things, and the third is the schema

"Two things, neither of which is a signature change" is wrong about the count and
about the sentence it excludes. Neither claim above has a subject until the
document can hold a fan-in, and today it structurally cannot: `Edge` carries
`upstream` and `downstream` and no port, `Pipeline._referential_integrity`
raises "two edges feed X" over a set of fed nodes, and `Dag._elements` and
`_element_names` were deliberately given the same refusal
([a-nodes-inputs-are-labeled-and-variadic.md](a-nodes-inputs-are-labeled-and-variadic.md))
so that no site silently keys on the first of two. `accepts` naming one stream
and `ToolRun` taking one window are the other two,
[11.3](the-first-multi-input-tool-lifts-the-merge-deferral.md) says this step
retires all three, and nothing in this body said so.

So the port field lands here — the day `Edge` refers to has arrived when this
item runs, which is what its docstring says it is waiting for, and the second
`-k` term above cannot be written without it. Five refusals retire together with
it — `Pipeline`'s, and the four `(parent,) = fed` unpacks, three in `dag.py` and
one in `executor.py`. Each was written as a posture rather than an oversight, so
retiring one is replacing it with the variadic answer it predicted rather than
deleting it. `with_node_after`
and `without_node` carry ports through the splice, and `without_node`'s fan-out
of a removed node's inputs is already written for the case.

The pool item [choosing-among-sources-is-a-move-no-intent-kind-makes.md](choosing-among-sources-is-a-move-no-intent-kind-makes.md)
is what writes an edge the user re-pointed, and it is deferred on nothing —
re-pointing needs two producers, not two ports — so whichever runs second inherits
the other's shape rather than the two colliding.

## Reviewed 2026-08-10: done, and the refusals the fold authorised carry no case

Criterion re-run green at `a318b55`, whole suite 1287 green, ruff clean. Both
its cases were held under an independent mutant rather than taken from the
transcript: zeroing `port_delay` in `_bind` fails the alignment case on the
frame-index guard, and dropping the port from `node_key`'s pairs fails the
eleven `a_version_bump_moves_the_key` goldens. The crossing case itself
survives that second mutant — it certifies that the `upstream` position is
*ordered*, which is the whole of its claim given `Dag.inputs` sorts by port,
and the goldens are what pin the pairing.

Both of this body's clauses landed and the fold's five refusals retired as
predicted. What the fold authorised beyond them arrived with no subject: the
`Edge.port` validator and its absent-port serializer, `ToolSpec._check_ports`'
three refusals, `PortError`, `Pipeline`'s per-port collision on a *named* port,
and `offered_tools` skipping a merge. That residue has a home in
[the-port-refusals-and-the-portless-edge-have-no-case.md](the-port-refusals-and-the-portless-edge-have-no-case.md),
minted with this review — the search for an existing owner came back empty,
since every `have-no-case` item in the pool is per-module and these refusals
did not exist this morning.
