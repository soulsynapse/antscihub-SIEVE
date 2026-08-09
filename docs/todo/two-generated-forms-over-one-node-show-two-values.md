---
title: Two generated forms over one node show two values
priority: normal
phase: 9
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k both_forms_agree"
opened: 2026-08-09
---

# Two generated forms over one node show two values

09.1 put a `ParamForm` on every card of the pipeline stack, and the step
position already had one for the node the walk is on. Both are generated from
the same spec over the same node, both write through `issue`, and neither reads
the document back — which is `param_form.py`'s rule, deliberately: "a rebuilt
form is how new values arrive", because a form that patched itself in place
would be a second writer of the value it is showing.

With one form in the window that rule cost nothing. With two it is visible: an
edit committed on the card is not shown by the step position's form, and an edit
committed on the step position is not shown by the card, until something rebuilds
both. `app._redraw` is the only thing that does, and it runs on a move of the
walk. The arrow on a card happens to route through `_walk_to` and so rebuilds
even when the index does not change; the Right key does not, so the reachable
gesture is: edit a knob on the card, press Right, read the old value on the form
that is about to be committed from.

Two shapes, and the choice between them is what this item is for rather than a
detail of the fix. Rebuilding the pane the user is *not* standing on is cheap and
keeps the read-once rule intact, but it puts "which position is showing" into the
edit path, and a rebuild triggered by a live drag would delete the control under
the cursor if the sides were ever confused. Having the surfaces learn from the
write and refresh only the sibling widget for the parameter that moved is the
narrower fix and is a step back toward a form that reads the document, which is
the thing the rule forbids. Whichever lands, the case has to drive a real
`MainWindow` and assert both directions, or it passes on a window where only one
of the two forms was ever built.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k both_forms_agree
    132 deselected in 0.66s
    exit: 5
