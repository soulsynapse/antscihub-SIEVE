---
title: A merge keys its inputs by port, and swapping them moves one key
status: deferred
deferred_for: subject
gated_on: the first two-input tool, which is what gives `a - b` and `b - a` a subject
priority: normal
phase: "03"
opened: 2026-08-07
---

# A merge keys its inputs by port, and swapping them moves one key

v2 asserted `swapping_a_merges_ports_moves_its_key_and_only_its_key`: two
inputs crossed over on a merge node produce a different key for that node and
leave every other key standing. Schema v1 gives a node one input and an edge no
port (`core/tool_base.py`), so the case has no subject and was dropped from
03.3's table and again from 03.4.1's — this is where it lives until it has one.

What has to change with it, rather than after it: `cache_key.node_key` takes
`upstream` as a single key and its docstring already says the day a two-input
tool lands is the day this position becomes port-bound pairs again, and
`Dag.node_keys` unpacks a one-element `upstreams` tuple so that keying on the
first of two is a raise rather than a silently wrong key. Both are written to
fail loudly at that moment; the test is what would make them fail for the right
reason.
