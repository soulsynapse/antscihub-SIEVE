---
title: The pipeline pane is a stack of cards wearing the referent's chrome
step: "09.1"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k chain_cards"
opened: 2026-08-09
---

# The pipeline pane is a stack of cards wearing the referent's chrome

The walk's pipeline position shows one card per live step — title, knobs, and
plots on the card, stage headers with their `in -> out` chips between groups,
a fixed project card standing above the scroll — with click-select moving the
same selection ↑/↓ moves, and a → button on each card that selects the step
and slides to its form. MOCKUP-MAP.md rows: "Settings is the right pane",
"Card verbs" (the select and → halves only; pin, remove and swap are later
steps), and "Chrome" — `ChainCard`, `_card`, `_stage_header`,
`_stack_stylesheet`, `_darken_title_bar` in the referent. The chrome rides
with this step because the stack's stylesheet is where it lives: dark
throughout including the OS frame, scrollbars left to the platform. Knob
widgets come from the Phase 7 generator, not from a per-step table — the
referent's `_knobs_for` is keyed by position because a mockup has no specs,
and copying that shape would be a `tool_id` branch.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k chain_cards
    119 deselected in 0.68s
    exit: 5
