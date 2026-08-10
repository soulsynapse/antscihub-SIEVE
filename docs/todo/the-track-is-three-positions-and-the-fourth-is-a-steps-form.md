---
title: The track carries a fourth position for a pane that is one step's form
phase: 9
priority: normal
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k the_track_has_three_positions"
opened: 2026-08-10
---

# The track carries a fourth position for a pane that is one step's form

[MOCKUP-MAP.md](../MOCKUP-MAP.md)'s "Settings is the right pane" row opens
"Three sliding positions: project ⟷ pipeline ⟷ step", and its "Output is a
step" row says the run/save screen is dissolved. The tree's track is four wide:
`gui/control.py` holds `_POS_SAVE`, `POSITION_NAMES` counts four, `show_save`
and `set_save_screen` are its own methods, and the module's docstring argues at
length — "Why save is a fourth position and not a dialog" (07.11) — for the
shape the referent overrules.

09.2 saw this and left it deliberately: its work note says "What was *not* done
is folding the fourth position of the track away … neither this item nor ADR 25
rules on the track", and it is `done` on a criterion that never covered the
track. So the fourth pane is not a survivor that 09.2 missed; it is a ruling
09.2 declined to make on its own, and this item is where it gets made.

What makes the present state incoherent is not the count but what stands at that
position. The save pane *is* the output step's form — the card's `→` opens it
and Run sits on it, exactly as it does for every other step — so it is the one
step's form that does not live at the step position, and it is reachable by two
routes that arrive at the same widget. The pipeline stack numbers eleven cards
and the walk stands on ten of them.

Which reading the criterion is named for, and why. VISION's argument in
`control.py` — the last thing the user does should be on the line they have been
walking, not a modal over it — is *satisfied* by the output card: the card is at
the foot of the chain, its form is at the step position like any other, and
nothing becomes a dialog. That reading loses nothing VISION asked for and drops a
duplicate route, so the criterion is named for it. A session that rules the other
way renames the test and says why here.

The cost is real and is the substance rather than a detail. 09.2 put the output
card in `chain_stack.ChainColumn` "as a card of `ChainColumn` and not of the
walk, because the walk stands only where a node is" — `Project.outputs` is not a
`Node`. So folding the fourth position away needs one of: the walk gaining a
place to stand that is not a node, or the step position learning to hold a form
built from something other than a `Node` and a `ToolSpec` (`StepPane`'s
signature is both). Neither is a rename. The rail (`gui/rail.py`) counts what
the walk can stand on and would move with whichever answer lands, and
`gui/hotkeys.py`'s ←/→ reach the fourth position today only because the track
has one.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k the_track_has_three_positions
    223 deselected in 0.65s
    exit: 5

## 2026-08-10 (review): the canvas has a clause waiting on the same ruling

Folded in rather than minted, because it is a consequence of the sentence this
item already owns — "the walk stands only where a node is" — and not a second
subject. `the-canvas-shows-the-result-over-the-input.md` (10.1) asserts among
its clauses that "the output card shows the last real step's result", and that
clause has nowhere to land for exactly this reason: `MainWindow._order` is
`walk.node_order(pipeline)`, `_at` indexes it, and the output card is a
`chain_stack.Outputs` assembled from `kept_products` rather than a `Node`. The
walk cannot arrive there, so `_paint_viewport` has no state in which it is
standing on an output card and nothing about the canvas can be written for it.
10.1's review struck the clause and points here.

This does not widen what has to be decided — it is the same fork the paragraph
above states, the walk gaining a non-node place to stand or the step position
learning to build a form from something other than a `Node` and a `ToolSpec`.
It adds one consequence to whichever answer lands: the picture the canvas paints
at that position is the last frame-bearing node's result, which is what
`app.frame_bearing` already computes for every other card, so the canvas needs
no new rule and only a position it can be asked about.

The criterion above is named for the track's count and does not reach the
canvas. A session closing this item should widen it, or say here why the
canvas half is a separate close.
