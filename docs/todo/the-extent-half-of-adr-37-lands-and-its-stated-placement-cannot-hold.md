---
title: The extent half of ADR 37 lands, and the placement its text names cannot hold
priority: high
phase: 9
status: deferred
deferred_for: decision
gated_on: "Kendrick ruling on ADR 37's placement sentence"
opened: 2026-08-10
---

# The extent half of ADR 37 lands, and the placement its text names cannot hold

[adr/a-parameters-space-is-resolved-by-the-graph.md](../adr/a-parameters-space-is-resolved-by-the-graph.md)
settles two spaces: the axis a `BAND`'s handles are read on, and the extent of
the frame a `REGION` or a `POINT` indexes. Only the axis half is built
([a-surface-carries-its-values-and-not-the-axis-they-sit-on.md](a-surface-carries-its-values-and-not-the-axis-they-sit-on.md)).
The extent half is what the ADR names as the hole that predates the display
channel — `crop`'s region is denominated in the frame its node reads, the window
knows only the footage's own size, and the editor is refused for every `crop`
that is not a graph root — and nothing in the pool carries it.
[one-magnifier-and-everything-on-it-maps-to-source-pixels.md](one-magnifier-and-everything-on-it-maps-to-source-pixels.md)
is not its home: that is the zoom mapping between two widgets in different
units, and this is what the *document's* numbers are denominated in, which is
the same distinction the ADR draws between what a tool declares and what the
GUI resolves.

The decision this waits on is not the extent. It is one sentence of the ADR the
axis half already contradicts. ADR 37 says the per-node conversion sits beside
`node_element`, the walk sits in `pipeline/dag.py`, and the resolved value
"folds forward beside `elements` and `source_indexed`". The first is true in the
tree; the third cannot be, and the second is true only of the element walk the
axis borrows. `Dag` is built from a `Pipeline` with no replicate, and an axis
derived from a parameter — `default_freqs(params.fps)` — differs on every
replicate that deviates on it, so a `Dag` field would be the baseline's answer
served to a replicate that is not the baseline
([findings/2026.08.10-a-params-dependent-fold-cannot-live-on-the-dag-because-the-dag-is-replicate-agnostic.md](../findings/2026.08.10-a-params-dependent-fold-cannot-live-on-the-dag-because-the-dag-is-replicate-agnostic.md)).
The axis half resolves at the point of use in `gui/app.py` instead. A crop's
extent is params-dependent for exactly the same reason, so building the extent
half without a ruling would put the same contradiction in the tree twice and
make the ADR's text harder to correct rather than easier.

Under "ADRs have succession, not edits" this is Kendrick's and not a worker's.
The three answers, so the ruling has something to choose between. A successor
ADR restating the placement as *resolved where read, from a walk the graph
supplies*, which is what the tree does. Or the sentence read as naming the walk
rather than the field, in which case ADR 37 stands and this item is ordinary
work. Or a `Dag` built per replicate, which restores the placement literally and
puts a graph rebuild on the tuning loop's path — the one answer with a cost
nobody has measured.

`done_when` is owed the moment the deferral lifts. What it would assert is that
a `crop` well downstream of the root gets its region editor, and that the box
drawn on it lands in the frame that node actually reads rather than in the
footage's own pixels — which is the extent fold cashed in, and is the assertion
that cannot be written until the ruling says where the fold lives.
