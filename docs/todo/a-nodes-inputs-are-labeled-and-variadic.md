---
title: A node's inputs are labeled and variadic, not a left and a right
status: open
gated_on: nothing
priority: normal
phase: "03"
opened: 2026-08-07
---

# A node's inputs are labeled and variadic, not a left and a right

Two sites are written to fail loudly the day a node gets a second input rather
than key silently on the first: `cache_key.node_key` takes `upstream` as a
single key that is "not optional and not a mapping", and `Dag.node_keys`
unpacks `(parent,) = fed` so that a second entry raises. Three more predict
that day in prose — `Dag.upstreams`, `Edge`, and `tool_base`'s cut merging
protocol. All five predict it as a *pair*: `node_key`'s docstring says the
position "becomes port-bound pairs again", and `Edge` says the document learns
"which input an edge feeds".

The pair is the wrong prediction, and that is decided rather than proposed.
[VISION.md](../VISION.md)'s folder scenario has a user open a folder of videos
and be offered a concatenate-videos tool as one of two readings of it, and that
tool takes an arbitrary number of files. A pair-shaped contract would be
revised the day it landed, so the shape these five sites should predict is
labeled and variadic: an edge carries a port label, and a node's inputs are an
ordered mapping of them.

What should be different when this is done is only the prediction. The five
sites say what actually arrives, the two fail-loud raises stay fail-loud and
keep raising for the same reason, and no port field is added to the schema —
adding one now is the distinction-nothing-can-make that `Edge` already refuses.
The claim that a crossing moves exactly one key still has no subject and is
still deferred on the tool that would give it one; it lives in [a merge keys
its inputs by port](a-merge-keys-its-inputs-by-port.md).
