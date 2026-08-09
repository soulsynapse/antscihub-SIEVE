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

The shape the inputs arrive in is settled and is not a left and a right: an
edge carries a port label and a node's inputs are an ordered mapping of them,
which is what [VISION.md](../VISION.md)'s folder scenario asks for when it
offers a concatenate-videos tool over a folder. Most of the tree already
predicts that shape rather than a pair; what does not agree is what the sites
*do* with a second upstream, and that half could be answered against today's
tree and was split off to be — [two raise, two fold the
first](a-nodes-inputs-are-labeled-and-variadic.md). `a - b` versus `b - a`
stays the case *this* claim is about regardless: swapping two labels is what
has to move exactly one key and leave the rest standing, and two is the
smallest crossing that can show it.

The gate does not move. A scenario naming a tool is not the tool, and what this
item needs is a node that actually has two inputs to cross over.

## Ruled 2026-08-09 (Kendrick): a blocker, not a revival row

Considered for PLAN's "Not built, and what revives it" table and ruled
against: multi-input is settled in the referent — ports named at fan-in,
VISION's branch feeding a subtraction — so the trigger is unscheduled, not
hypothetical, and the deferral stands as written. Two notes for whoever the
gate eventually lifts for. First,
[adr/the-output-card-is-a-picture-of-the-write-list.md](../adr/the-output-card-is-a-picture-of-the-write-list.md)
closed the route 09.2 once promised — the output card gains no schema
inputs, so ticks will never be this item's subject; only a real multi-input
tool will. Second, this gate is prose and invisible to the index's
named-gate scan, so the item that mints the first multi-input tool must cite
this one in its body — that citation is the whole net.
