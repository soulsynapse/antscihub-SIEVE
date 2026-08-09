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
