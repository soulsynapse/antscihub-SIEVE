---
title: The swap menu holds what matches, not what admits
status: open
gated_on: nothing
priority: normal
phase: "9"
done_when: "uv run pytest tests/gui -q -k swap_menu"
opened: 2026-08-09
---

# The swap menu holds what matches, not what admits

Each card carries a ⇄ button whose menu is the offering for that position:
what could stand there, derived by `matches` from what flows into the
position against the shelf's declarations, displayed by match specificity.
Choosing an entry swaps the step through the ordinary command path.
MOCKUP-MAP.md row "Swap is a dropdown" — `_swap_button` in the referent,
whose `SWAPPABLE` table is sample data standing in for exactly this
derivation, and whose menu-only behaviour is the mock shortcut the map
names. No wizard, no dialog; the add-tool box (VISION's new-project
scenario, the gap ADR 22 carves out of its popup default) renders the same
shortlist at the foot of the stack, and lands with this or immediately
after it, whichever the tree makes cheaper.

## Folded 2026-08-09: the menu is empty at eight of ten positions today

`matches` and `offered_tools` landed in `core/tool_registry.py`, and measuring
them against the real shelf says the menu this item builds would be empty
below `crop`, `normalize`, `span`, and six others —
[findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything](../findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md)
has the table. That is not a defect in the predicate: a preserving tool emits
`ArraySpec()` because it emits what it was handed, and nothing folds dtype and
channels forward along the walk the way `Dag.elements` folds element meaning.
So this item has an empty-menu case to draw before it has a populated one, and
whether the ⇄ button is even shown at a position with nothing to offer is a
question the mock does not answer.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k swap_menu
    119 deselected in 0.66s
    exit: 5

## Folded 2026-08-09: the referent now has the box, and it is not at the foot

The paragraph above says the add-tool box "renders the same shortlist at the
foot of the stack". The mockup has it now and it does not stand there: ADD STEP
on the project card opens a card-shaped box in whichever gap the walk is on,
↑/↓ move it through the gaps, and the offer rewrites per position. The foot is
where VISION's scenario stands, not what a position is — the derivation is the
same at every gap, so a box fixed to the last one would be the same computation
displayed at one of the places it applies. `MOCKUP-MAP.md` row "Adding a step"
is the shape; `_AddBox`, `offer_after` and `add_node` are the referent's.

Two things that changes for this item. The offering must be answerable for a
gap that holds no tool, not only for a card that does — the referent keys both
on the same stage signature, and `offered_tools` already takes the upstream's
`emits` rather than anything about the tool standing there, so this is a
naming question and not a second predicate. And the splice the box implies —
the new step reads the gap's step, whatever read past the gap reads it — has no
intent under it: `session/intents.py` has `RemoveNode` and
`pipeline_model` has `without_node` with no counterpart, so the add site needs
the inverse built before any surface can emit it.

## Ruled 2026-08-09 (Kendrick): the gate lifted, the item opens

The deferral was on the offering predicate landing, and it has:
`the-offering-predicate-is-not-the-edge-legality-check.md` is done and
`matches` is on the contract (`core/tool_base.py`). The original gate text
lived in the frontmatter and is preserved here: *"the offering predicate
landing … the ⇄ menu renders the `matches` shortlist, and building the
button before the predicate would ship a menu with either everything or a
hardcoded list in it."* The empty-menu fold above stands: eight of ten
positions offer nothing today, so the empty case is still the first case.
