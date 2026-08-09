---
title: The swap menu holds what matches, not what admits
status: deferred
deferred_for: subject
gated_on: the offering predicate landing (the-offering-predicate-is-not-the-edge-legality-check.md, ruled 2026-08-09) — the ⇄ menu renders the `matches` shortlist, and building the button before the predicate would ship a menu with either everything or a hardcoded list in it
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

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k swap_menu
    119 deselected in 0.66s
    exit: 5
