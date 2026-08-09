---
title: A checkpoint does not record which product of a tool it holds
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# A checkpoint does not record which product it holds

`ToolSpec.emissions` (05.4) says a node of `block_signal` can emit any of four
measurements and a node of `background_ema` either half of one model. The
manifest `storage/checkpoint_writer.py` writes records the node id, the cache
key, the span, the dtype and the shape — everything except which of those
products the file in front of the reader actually is.

Recoverable today, because the params are in the project document beside it and
the selecting parameter is one lookup away. That is the same argument v2 made
for leaving a fact out of an artifact and then had to walk back: the file is
what a reviewer opens, and a `.npy` of float32 that could be coherence or flow
speed is one a reader cannot check against the claim it was made for.

Not urgent and not sequenced: the reader that would consume it is the read-back
path, and the save screen that writes one file per checked emission is Phase 7.
Whichever arrives first is where this is answered — as a manifest field the
writer is handed, not one it derives, since the writer takes outputs and knows
nothing about tools.

## The save screen arrived first and could not answer it (2026-08-08, from 07.9)

`gui/save_screen.py` offers a checkbox per *product* — every `Emission` of every
node, which is what VISION's list is — and writes `Project.checkpoints`, which is
node ids. So two products of one node check independently and write the same
entry: ticking `coherence` on a node already kept for `flow_speed` changes
nothing in the document, and unticking one of the two leaves the node kept. The
screen holds the honest half it can, showing a kept node ticked against the
product its parameters currently select, so what is on screen is the file a run
would write — but that is a rendering rule, not a record.

What the clause above anticipated is therefore still owed, and the shape of it
has moved: it is no longer only a manifest field, because the *document* cannot
say which product was asked for either. `checkpoints: tuple[str, ...]` is the
field that would have to grow, which makes this a schema question ahead of a
writer one, and neither 07.9's criterion nor its cut could reach it.

## 2026-08-09: the read-back path arrived first, and it is next in the queue

"Whichever arrives first is where this is answered" resolved toward the
read-back path:
[crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md)
is at the head of the queue and mints the checkpoint file's key-bearing
identity under `adr/a-root-keys-by-its-reader.md`, so the schema question is
answered there — a paragraph in that item now points back here. This one
stays open as the record of the gap until the answer exists to point at.

## 2026-08-09: the artifact half landed; the document half did not

From [a-checkpoint-is-read-back-as-a-source-tool.md](a-checkpoint-is-read-back-as-a-source-tool.md).
`tool_base.selected_emission` derives the product a node's resolved parameters
compute, `cli/run_cmd.py` hands it to the writer per checkpointed node, and
`storage/checkpoint_writer.py` puts it in the manifest entry *and* in the file
name — `<node>.<emission>.npy`. The name is where it had to be rather than the
manifest alone: a read-back root is keyed off
`cache_key.source_identity` of its file, which is a path and two stats, so a
name that skipped the product would key two products of one node alike. The
first paragraph's "a `.npy` of float32 that could be coherence or flow speed" is
therefore no longer a file a reader cannot check.

**What is left is the half the save screen ran into, and it is unchanged.**
`Project.checkpoints` is still `tuple[str, ...]`, so the *document* still cannot
ask for two products of one node — and it turns out it never needed to for the
artifact to be honest, because the selecting parameter picks one product per
node per run and the writer records what that run computed. The open question is
narrower than the second section states: not "which product is this file", which
is answered, but whether a user checking two products of one node is asking for
two runs, two nodes, or a schema that can hold both. `gui/save_screen.py` still
carries the rendering rule and its docstring still points here.

**A second fact the manifest does not record, and it arrived with the reader.**
`tools/checkpoint.py` declares `element=None` — undeclarable — because a `.npy`
records dtype and shape and never what one value is a value of, and a source
tool has no upstream to preserve a meaning from. `ToolSpec` now admits that for
a source tool and for no other kind. So a detector wired over a read-back signal
has no noun to count in and `Dag.element_lost_at` names the checkpoint node.
Recovering it is this item's shape exactly: an element field the writer is
handed, and a parameter on the read-back tool that carries it. Not urgent for
the same reason as the rest — nothing outside `dag.py` reads `Dag.elements`
yet — and folded here rather than minted because it is the same manifest, the
same writer, and the same sentence about what a checkpoint fails to record.

## 2026-08-09 (from 09.2): the card draws a list the form cannot tick

The output card at the foot of the chain is a picture of what the run keeps, and
what the run keeps is `Project.checkpoints` *and* `Project.outputs` — both, since
a sink is a thing the run writes and a picture reading one of the two would go
quiet about the other (`gui/save_screen.kept_products`,
[adr/the-output-card-is-a-picture-of-the-write-list.md](../adr/the-output-card-is-a-picture-of-the-write-list.md)).
The form behind that card ticks only the first of the two: a checkbox writes
`checkpoints` and `SetOutputs` carries the sinks through untouched, because
nothing on the screen names a format or a directory and the map's review leaves
that combo unsettled. So a document holding a sink — hand-written, or arrived
from a handoff — draws an edge into the card that no box on its own form is
ticked for.

Folded here rather than minted because it is this item's sentence from the other
side. The screen's checkbox is `checkpoints`-shaped, and both gaps are that shape
failing to hold what the document can say: two products of one node above, and a
sink at all here. Whatever answers the first has to decide whether a tick is one
list or two.
