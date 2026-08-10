---
title: Swap opens the same box, and keeps the node it is
step: "09.10"
status: done
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'swap_box or keeps_the_node'"
opened: 2026-08-09
---

# Swap opens the same box, and keeps the node it is

There is no swap menu. A card's ⇄ opens the box
[09.9](a-gap-is-a-position-and-the-box-fills-it.md) builds, standing where that
card is instead of in a gap, lit on the tool already there — the checked entry
the menu was going to carry. Anchored: ↑/↓ have nothing to move, ←/→ still walk
the offer, esc restores the card. MOCKUP-MAP.md row "Swap is the same box";
`_swap_button`, `offer_at`, `retool` and `Control.swap_here` in the referent.

**Taking an offer here keeps the node's identity, and that is the whole of what
distinguishes it from removing a step and adding one.** `Project.without_node`
(`core/pipeline_model.py`) drops the node's replicate overrides, its
checkpoints, its sinks and its `input_hashes` entry, and `node_id` is what names
the artifact on disk and what `bench/` addresses — so a swap done as a remove
and an add would break every one of those references with nothing going red: the
run writes different files and the output card is quietly emptier. This needs a
mutation that replaces the tool and holds the id, a third intent beside
`RemoveNode` and 09.9's splice, under a gesture that looks identical to both.

What does *not* survive is the params, and that is right rather than a
shortfall: they were the departed tool's. The referent shows it by dropping a
swapped position's knobs, plots and guidance (`RETOOLED`) while its edges and
the ticks naming it stay.

The empty offer is sharper here than in 09.9: a ⇄ on a position offering
nothing would take the card away and leave esc as the only exit, where an empty
menu is merely useless. Whether the button is shown at all at such a position is
this item's to answer, on the same measurement 09.9 faces.

**Folded 2026-08-09 (review of 09.9): the box over a fanned card is painted
and asserted nowhere.** 09.9 taught `ChainColumn` to dash the edges a box
would be spliced onto, and gave `fanned_edge` a `dst` argument so the crop
fan's way out lands on the box when the box stands in the gap the fan hangs
in. Nothing enters that branch: the 09.9 fixture's project declares no
regions, so no case in the tree has a fan and a box on screen at once, and
`_paint_fanned_edge(provisional=True)` is reached only through `paintEvent`
(`findings/loop/2026.08.09-an-items-clause-that-lands-only-in-paintevent-is-outside-every-oracle.md`).
The geometry is testable without pixels — `fanned_edge(dst)` returns the runs
and drops — and the anchored box lands on a card rather than in a gap, so a
swap over `crop` is exactly where a picture that says two things at once
would show up. One case with regions declared covers both gestures.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k 'swap_box or keeps_the_node'
    181 deselected in 0.66s
    exit: 5

## The row this item was minted as, now overtaken

Kept because the folds below answer to it, and because what changed is worth
seeing: this began as a dropdown, and merging it into the box is Kendrick's
ruling of 2026-08-09 rather than a restatement of it.

> Each card carries a ⇄ button whose menu is the offering for that position:
> what could stand there, derived by `matches` from what flows into the
> position against the shelf's declarations, displayed by match specificity.
> Choosing an entry swaps the step through the ordinary command path.
> MOCKUP-MAP.md row "Swap is a dropdown" — `_swap_button` in the referent,
> whose `SWAPPABLE` table is sample data standing in for exactly this
> derivation, and whose menu-only behaviour is the mock shortcut the map
> names. No wizard, no dialog; the add-tool box (VISION's new-project
> scenario, the gap ADR 22 carves out of its popup default) renders the same
> shortlist at the foot of the stack, and lands with this or immediately
> after it, whichever the tree makes cheaper.

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

The overtaken row above says the add-tool box "renders the same shortlist at
the foot of the stack". The mockup has it now and it does not stand there: ADD
STEP
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

## Ruled 2026-08-09 (Kendrick): one surface, two mutations

There is no swap menu. ⇄ opens the same box the gaps get, standing where the
card is instead of between two — the card ghosts under it, the tool already
there is the lit offer, esc restores. Both are the same question asked of a
position, and two widgets rendering one derivation was the duplication this
dissolves.

**The box never writes on open.** Opening is picker behaviour: the provisional
removal is surface state, one mutation is issued when an offer is taken, and
esc costs nothing. Already true of add; this makes it the rule, and it is what
the "esc restores" above is standing on.

**A swap keeps the node's identity, so it is not remove-then-add.** They look
identical and are not the same write. `Project.without_node`
(`core/pipeline_model.py`) drops the node's replicate overrides, its
checkpoints, its sinks and its `input_hashes` entry, and `node_id` is what
names the artifact on disk and what `bench/` addresses — so a swap that minted
a new id would break every reference silently, with the run writing different
files and the output card quietly emptier. In the referent the same thing shows
as the write list: swapping `count-1` would untick both of its products. So the
swap site needs a mutation that replaces the tool and keeps the id, and it is a
third thing beside `RemoveNode` and the add splice this item already owes —
three intents under two gestures on one widget.

**An anchored box has one fewer axis, not a different keyboard.** A box opened
by ⇄ does not move: it is standing at a position that exists, and letting ↑/↓
walk it into the gaps would flip it between replacing and inserting as it
travelled, which the user could not read off the screen. ←/→ still walk the
offer in both, and ↑/↓ have nothing to move in this one — the reading to
check when it is built, not a second key map to write.

The empty offer gets sharper here than it is for add: ⇄ on a position with
nothing to offer would ghost the card and leave esc as the only exit, where an
empty menu is merely useless. Same answer needed, worse failure.

Building this deletes `_swap_button`'s menu from the referent and rewrites
`MOCKUP-MAP.md`'s "Swap is a dropdown" row. That is a licensed revision of
[a-position-is-asked-for-in-the-chain](../adr/a-position-is-asked-for-in-the-chain.md),
not a succession of it: the ADR rules that a question about a place is asked in
the chain, and this is that rule reaching a second gesture.

## Closed 2026-08-09 (review)

`done_when` re-run green (8 passed), the full suite 1196 passed, and five
mutants over the anchoring, the fan suppression, the empty-offer refusal, the
landing position and the override drop all KILLED. Two corrections to the prose
above rather than to the work: the referent paragraph one line up was already
discharged before this item was worked — `a5b1adc` made `mockup/_swap_button`
open the box and rewrote the map's row to "Swap is the same box" — so nothing in
the referent was owed by the build, and the offer's lit entry got a consequence
the ruling did not follow through on, which is
[taking-the-tool-already-there-wipes-the-step-it-kept](taking-the-tool-already-there-wipes-the-step-it-kept.md).
