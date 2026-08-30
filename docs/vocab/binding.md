---
title: binding
group: Substrate
position: 8
gloss: The join between an edge one node wants and an edge another offers, made by name and not by wire — and where every fact a producer could not honestly state about itself gets worked out.
origin: emergent
defined: 2026-08-30
---

The join between an [edge](edge.md) one [node](node.md) wants and an edge
another offers, made by name and not by wire. A binding is where a
[step](step.md) stops being an isolated arithmetic and acquires a timebase, an
extent and an access mode — none of which it declared, all of which follow from
what feeds it. It is a derivation before it is a connection, which is why it is
a word and not just a pointer.

## Where it lives

`bind` in `experiments/chain-experiments/bind.py`: hand it a `Step` and the
`Output` above it, get back the `Output`s that step offers. Timebase and origin
are the input's. `listed` is the input's less the first `reach`, because a step
admitting -30 has no honest answer for the first thirty positions. `access` is
`RANDOM` and pointedly *not* the input's — a step's output is read out of where
it was kept, so a forward-only input still yields a randomly readable output
once ADR-0005 has done the recording. The [ordinals](ordinal.md) are
snapshotted at bind, or a growing extent would renumber rows already written.
Run 2026-08-30 over two steps of different reach: heads at `listed[reach]` came
out 30030 and 1001, 29 rows apart, one positioning for both over a FORWARD
input.

`Produced` in `contract/nodes.py` exists because of this — "the step says the
name, the kind and the dtype, and the binding says the rest" — and
`contract/edges.py` says an edge name "is what a binding names".
`video_file_source.py` and `image_directory_source.py` were written apart and
both index their edge name against a stream that does not exist yet.

Two things unsettled, neither about the meaning. Nothing in `src/` binds, so
the pipeline view's arrows are still drawn from adjacency ([edge](edge.md)).
And the consumer end has no agreed name: `gui/frame/window.py` and the leads
call it a port, `contract/edges.py` calls it an edge.
