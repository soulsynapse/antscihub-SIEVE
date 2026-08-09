---
title: Remove reads past the step it drops
step: "09.4"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k reads_past"
opened: 2026-08-09
---

# Remove reads past the step it drops

Each card carries a ✕, and removing a step closes the chain over it rather
than breaking it: whatever read the removed step inherits its inputs — both
of them, where the removed step merged two — and the walk and the pin land on
the step above, the nearest surviving place the user was standing. The source
is offered disabled rather than omitted, so the buttons hold their positions
on every card; a chain with nothing to read is not a shorter chain.
MOCKUP-MAP.md row "Card verbs", ruled intent by Kendrick in the map's review;
`_remove_button`, `_sources_of` and `Control.remove` in the referent.
This is the surface that arrives with `RemoveNode` (PLAN Phase 7's command
list: "AddNode and RemoveNode arriving with the surfaces that emit them"), so
the read-past semantics land in the command layer as the document mutation,
with the GUI emitting the intent — not as a display-side fiction over an
unchanged graph.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k reads_past
    119 deselected in 0.68s
    exit: 5
