---
title: The window grows a port-keyed form, and the executor delays each port to the slowest
step: "11.2"
status: open
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
