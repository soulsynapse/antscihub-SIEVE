---
title: binding
group: Substrate
position: 8
gloss: The join between an edge one node wants and an edge another offers, made by name and not by wire — and where every fact a producer could not honestly state about itself gets worked out.
origin: emergent
defined: 2026-08-30
---

The join between an [edge](edge.md) one [node](node.md) wants and an edge
another offers, made by name and not by wire, and the place every fact a
producer could not honestly state about itself gets worked out. A binding is
where a [step](step.md) stops being an isolated arithmetic and acquires a
timebase, an extent and an access mode — none of which it declared, all of
which follow from what feeds it. It is a derivation before it is a connection,
which is why it is a word and not just a pointer.

## Where it lives

`bind` in `experiments/chain-experiments/bind.py` is the whole idea in one
function: hand it a `Step` and the `Output` above it and it returns the
`Output`s that step offers. Each field comes from somewhere nameable. Timebase
and origin are the input's, carried untouched. `listed` is the input's less the
first `reach`, because a step admitting -30 has no honest answer for the first
thirty positions. `closed` is the input's, `window` is None because the series
is the retention, `starts` is None because every row reads back alike. `access`
is `RANDOM` and pointedly *not* the input's — a step's output is read out of
where it was kept rather than recomputed on the way past, so a forward-only
input still yields a randomly readable output once ADR-0005 has done the
recording. The [ordinals](ordinal.md) are snapshotted at bind for the reason
`Ordinals` is: a growing extent would otherwise renumber rows already written.

`01-derived-binding` ran this on 2026-08-30 against two steps of different
reach over one synthetic source: heads at `listed[reach]` came out 30030 and
1001 — 29 rows apart — one positioning for both steps over a FORWARD input, and
a read back out through the binding held. The pts is the number that matters
there, which is where the first version of that check went wrong.

Nothing decided this word either; it arrived from several directions at once
and always meant the same join. `Produced` in `contract/nodes.py` exists
*because* of it — "the step says the name, the kind and the dtype, and the
binding says the rest" — and a record that carried a form and a `Positioning`
and then refused to fill them would permit in its type what it forbids in its
checks. `contract/edges.py` says the name "is what a binding names — a document
and a key within it", which is the same shape `docs/architecture-leads.md`
gives a port: a requirement in the document that travels, resolved in the one
that does not. `video_file_source.py` and `image_directory_source.py` were
written apart and both index their edge name against a stream that does not
exist yet, each explaining itself as a binding that would otherwise break
silently. `gui/view/pipeline/view.py` labels a card's `offers` row "what the
next card in the chain would be binding to".

The collisions are all cross-domain and none is a contest: Python's own bound
method, in the comment most GUI primitives carry about PySide6 dropping a
connection with its receiver; key bindings, in `gui/frame/hotkeys.py` and in
ADR-0003's re-bound arrow keys; a language binding over a C library, in the
decode corpus, where `docs/decode/ideas.md` warns against "measuring a binding
and concluding about a codec"; and *bounded* as a limit, in `session.py`'s form
bounded to the proxy's long edge.

Two things the word does not yet settle, neither about its meaning. Nothing in
`src/` binds: this is one experiment plus the docstrings pointing at it, and
until it lands the pipeline view's arrows are drawn from adjacency rather than
from any join ([edge](edge.md)). And the consumer end has no agreed name — an
edge is "a named thing a node offers or wants", while the leads and
`gui/frame/window.py` say a port is what gets bound to, so a want is a port in
one file and an edge in another. A binding joins the two under either reading,
which is why it is recorded here while that one is not.
