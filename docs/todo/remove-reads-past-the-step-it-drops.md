---
title: Remove reads past the step it drops
step: "09.4"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'reads_past or card_and_slot'"
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

## Folded 2026-08-09 at 09.3's review: the pinned card's note lies for a step whose surface is elsewhere

09.3 landed the second verb this item's head row is about, and put a note under
it: the pinned step's card carries `PINNED_ELSEWHERE_NOTE`, "surface pinned
below the canvas", so the stack says where the surface went rather than drawing
it twice. It is added on `position == pinned` alone, with no reference to
whether that step *has* a surface in the slot. Probed on the chain
`crop -> downsample -> detect` with `pin(0)`, card 1 reads

    ['1. crop', 'region', "{'x': 0, ...}", 'surface pinned below the canvas']

while the slot under the canvas reads `pinned.CANVAS_NOTE` — "the boxes on the
canvas are this step's surface — drag them there", which
`test_pinned_slot_evicts_and_a_step_with_no_plot_states_its_surface_in_words`
asserts. Two sentences on one screen disagreeing about where `crop`'s surface
is, and the card's is the wrong one: 09.3's own sentence is that the card says
where its surface *went*, and for a `REGION` step it went to the canvas, not
below it. `downsample` is the third case — no surface anywhere, and the card
still says one is pinned below the canvas.

It lands here because this item is the next thing to rewrite `_build_card`'s
head row and body (the ✕ beside the ◆) and the next thing to move `app._pinned`
— one commit covers the note and the verb. The shape is three notes keyed off
the same predicate `pinned.draws_a_trace` already answers for the slot, not two
independent strings; `PINNED_ELSEWHERE_NOTE` is only true where the slot's
surface is the graph.

`done_when` (`-k reads_past`) is not widened here and does not reach this: a
case asserting the card's note agrees with the slot's would be the part of this
paragraph a criterion can hold.

## Widened 2026-08-09 at this item's review

The paragraph above named the case it wanted and the criterion did not reach it,
so `done_when` now selects `reads_past or card_and_slot` — the second disjunct
is `test_pinned_slot_card_and_slot_never_disagree_about_where_the_surface_is`,
which would otherwise be certified only by 09.3's already-`done` criterion and
so by nothing that runs when this item is checked. Both disjuncts select (3 and
1); neither is a name that matches nothing.
