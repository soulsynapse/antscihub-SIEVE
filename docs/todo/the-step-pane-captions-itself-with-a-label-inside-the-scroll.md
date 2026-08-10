---
title: The step pane captions itself with a label that scrolls away
phase: 9
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k the_step_caption_is_a_fixed_card"
opened: 2026-08-10
---

# The step pane captions itself with a label that scrolls away

[MOCKUP-MAP.md](../MOCKUP-MAP.md)'s "Settings is the right pane" row ends "the
step pane is caption card, generated form, guidance expander". The tree has the
last two. In place of the first, `gui/step_pane.py` puts a `NodeBox` — a bare
`QLabel` reading `{position}. {tool_id}`, `gui/node_list.py`'s leftover from
before 09.1 made the pipeline position a stack — *inside* the scrolling column,
above the form.

Two things follow from where it sits. It is not in the stack's chrome, so the
one pane of the three that names what it is showing does it in the platform's
default dress while the project pane and the pipeline pane both carry a fixed
card (`chain_stack.py`'s header, `project_select.py`'s library card). And it
scrolls: open the guidance on a tool with a tall form and the pane stops saying
which step is being edited, which is the one thing a settings pane must not stop
saying when three surfaces over one node are already in play
([two-generated-forms-over-one-node-show-two-values.md](two-generated-forms-over-one-node-show-two-values.md)).
The referent's `build_step_pane` puts its card outside the scroll for exactly
that, and its comment states the parallel the row is drawn from: the card stands
"where the library card and the project card stand: the step is to its knobs
what the project is to its chain".

The chip is the half that cannot land here. The referent's card carries the
stage's `in -> out` chip beside the caption, and what a stage is has no answer in
the tree —
[a-stage-header-groups-cards-by-nothing-the-tree-declares.md](a-stage-header-groups-cards-by-nothing-the-tree-declares.md)
owns that ruling for the pipeline stack's headers and it decides this chip too.
So this item is the card and its position: fixed above the scroll, in the same
chrome the other two panes wear, naming the node the walk is on. A session that
finds the stage item already answered puts the chip on in the same commit; one
that does not leaves the slot and says nothing in its place.

`NodeBox` is then the caption's only remaining caller, and whether it survives as
a widget or the card is built where the other two are built is the work's call,
not a clause of this item.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k the_step_caption_is_a_fixed_card
    223 deselected in 0.70s
    exit: 5
