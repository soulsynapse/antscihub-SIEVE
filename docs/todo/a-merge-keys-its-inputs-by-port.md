---
title: A merge keys its inputs by port, and swapping them moves one key
status: deferred
deferred_for: subject
gated_on: the first multi-input tool, which is what gives `a - b` and `b - a` a subject
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

The shape the inputs arrive in is settled and is not a left and a right —
[a node's inputs are labeled and
variadic](a-nodes-inputs-are-labeled-and-variadic.md), which is the half of
this that could be answered against today's tree and was split off to be. `a -
b` versus `b - a` stays the case *this* claim is about regardless: swapping two
labels is what has to move exactly one key and leave the rest standing, and two
is the smallest crossing that can show it.

The gate does not move. A scenario naming a tool is not the tool, and what this
item needs is a node that actually has two inputs to cross over.
