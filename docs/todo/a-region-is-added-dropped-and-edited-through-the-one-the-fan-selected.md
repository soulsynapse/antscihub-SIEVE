---
title: A region is added, dropped, and edited through the one the fan selected
priority: high
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'adding_a_region_selects_it or a_knob_edits_the_selected_regions_own_value'"
opened: 2026-08-09
---

# A region is added, dropped, and edited through the one the fan selected

09.8 drew the fan and made a square selectable, and stopped there: the selection
is `MainWindow._region`, and the only thing that reads it is the arrowhead the
fan moves. Two halves of MOCKUP-MAP.md row "Crop cuts regions, plural" are not
built, and they are the halves that make the selection mean anything.

**The card holds the count and the two mini-buttons.** In the tree a region is a
`Replicate`, so + and − are document mutations and the command layer is the
document's only writer (`adr` and `session/intents.py`) — which today has
`SetParam`, `SetOutputs` and `RemoveNode` and no verb that adds or drops a
replicate. Adding one selects it, which is the fan's selection moving from a
gesture that is not a click on a square. A project reduced to no replicates is
the baseline again and the fan goes with it; whether − may take the last one is
the sub-question, and the referent's answer (`remove_crop` refuses below one) was
written for a mockup where a crop with no region was incoherent, which is not the
tree's case.

**A knob edits the region the fan is standing on.** `ParamForm`, `StepPane` and
`kind_editors` all write through `SetParam` onto `Node.params`, which is the
*baseline* for replicates that have not been configured — so with two regions
selected in turn, a box dragged on the canvas moves both. `pipeline_model`
already holds the shape this wants: `resolved_params(node, replicate)` for
reading and `deviation(node, replicate, params)` for writing, the latter written
precisely so that submitting a whole resolved view does not drag previously
pinned values into the baseline. What has to be decided rather than looked up is
what an edit means when no square is selected because the project has no
replicates — the baseline, presumably, which is what the surface does today and
would then be one arm of a branch rather than the only behaviour.

The two are one item because one commit satisfies both or neither: a + that adds
a region nobody can then edit separately is a count, and a per-replicate edit
with no way to make a second replicate has no case that discriminates it.
`done_when` names one case for each half.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k 'adding_a_region_selects_it or a_knob_edits_the_selected_regions_own_value'
    169 deselected in 0.94s
    exit: 5

## 2026-08-09 (review of 09.8): − has to move the selection, or the fan aborts the process

`MainWindow._region` is clamped in `select_region` and reset to 0 in
`open_project`, and nothing else moves it, so today it cannot exceed the
replicate count. The − verb this item adds is what makes it able to.
`ChainColumn.fanned_edge` indexes `tiles[self.fan.selected]` unguarded and runs
inside `paintEvent`: a `PipelinePane` built offscreen over two regions with
`selected=3` segfaults on `show()` rather than raising, because the IndexError
is thrown inside a Qt virtual override and PySide6 aborts. The same
construction at `selected=0` exits 0. So dropping a region while standing on
the last one is a process abort and not a stale picture — either − moves
`_region` on the way down or the fan clamps what it is handed, and the case for
it belongs with the verb that makes it reachable.

The other half of the same seam: `app.cuts_regions` decides which card the fan
hangs under, and its roots-only clause (`node_id in source_fed_nodes(pipeline)`)
is killed by nothing — replacing it with `True` survives
`uv run pytest -q tests/gui`. The + verb writes an override keyed on a node id
and that has to be the node the fan hangs under, so whatever pins the keying
pins the clause.
