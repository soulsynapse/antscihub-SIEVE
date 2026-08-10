---
title: Taking the offer the box opened lit on wipes the parameters of the step that stayed
status: open
gated_on: nothing
priority: normal
phase: "09"
done_when: 'uv run pytest "tests/gui/test_swap_box.py::test_taking_the_tool_already_standing_there_keeps_its_parameters" -q'
opened: 2026-08-09
---

# Taking the offer the box opened lit on wipes the parameters of the step that stayed

The anchored box opens lit on the tool already standing at the position —
[09.10](swap-opens-the-same-box-and-keeps-the-node.md) ruled that entry "the one
saying *and it could stay*", the checked row a menu would have carried. Enter is
what takes the lit offer. So the gesture that reads as *never mind, leave it*
issues `RetoolNode(node_id, <the same tool_id>, <the same version>)`, and
`Project.with_node_retooled` rebuilds the node as
`Node(node_id=..., tool_id=..., version=...)` with no params — the step's knobs
and every replicate's overrides on it are gone, while the picture, the edges,
the checkpoints and the sinks all say nothing happened.

Measured directly at the model layer: a `motion_history` node carrying
`tau_seconds: 2.5`, retooled to `motion_history 1.0.0`, comes back with
`params == {}`. On today's fixture chain the box over `motion_history` opens
`lit == 1` on `motion_history` itself, so the whole footgun is ⇄ then enter.

The write's own justification is what fails here rather than the write: both the
intent and the two model methods argue that the parameters go *because they were
the departed tool's*. When nothing departs there is no such argument, and the
sentence 09.10 lit the entry with — it could stay — is contradicted by what
taking it does. That is the reading to build to: the tool already there taken
again leaves the document byte-identical and closes the box, the same cost as
esc. It is undoable today (`session.can_undo()` is true after it), which is why
this is an item rather than a defect that had to block 09.10.

Not the same question as excluding the current tool from the offer, which would
be the other repair and is refused by the same ruling: the lit entry is what
tells the user what is standing there, and an offer that omitted it would open
lit on a stranger.

`done_when` at minting, red because the case does not exist (exit 4):

    $ uv run pytest "tests/gui/test_swap_box.py::test_taking_the_tool_already_standing_there_keeps_its_parameters" -q
    no tests ran in 0.14s
    exit: 4

## Folded 2026-08-10 at `531b878`'s review: the parameter it now wipes is the footage

`531b878` gave the root an offer of its own, so the source card's ⇄ is live and
the box over it opens lit on the source standing there — the same gesture, at the
one position whose parameter is the file the user picked. Retooling `footage` to
`footage` clears `path`, and the card the user is looking at goes back to reading
`UNCHOSEN` while the chain below it is untouched, which is a worse showing of the
same defect than a lost `tau_seconds`: the project stops naming its footage at
all. The measurement and the repair are unchanged — this adds the position where
the footgun is easiest to reach, not a second mechanism, so the criterion above
covers it once `with_node_retooled` stops arguing from a tool that did not depart.
