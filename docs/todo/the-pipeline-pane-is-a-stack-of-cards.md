---
title: The pipeline pane is a stack of cards wearing the referent's chrome
step: "09.1"
status: done
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

## Review note, 2026-08-09

`done_when` re-run green independently (`5 passed, 127 deselected`), whole
suite `1086 passed`, `tests/gui` alone exit 0, ruff format/check clean,
contracts 8 kept / 0 broken.

The five cases are non-vacuous by mutation rather than by the revert the run
offered — a revert that deletes `chain_stack.py` and `chrome.py` proves only
that the modules were new
([findings/loop/2026.08.07-reverting-the-implementation-is-no-proof-when-the-item-created-the-module.md](../findings/loop/2026.08.07-reverting-the-implementation-is-no-proof-when-the-item-created-the-module.md)).
Under `scripts/mutation_sweep.py`: dropping `_on_select()`, pinning `selected`
to `False`, and pointing the arrow at `current` instead of `position` are all
KILLED; `.QWidget` widened to `QWidget` and the window sheet narrowed onto
`QWidget` are both KILLED, so the two-selector claim is pinned to the
selectors and not to a colour. The fixture's `close()` is load-bearing —
replaced by `pass`, `tests/gui` is KILLED, which independently reproduces the
abort
[findings/2026.08.09-the-players-destroyed-net-does-not-catch-a-window-nobody-closed.md](../findings/2026.08.09-the-players-destroyed-net-does-not-catch-a-window-nobody-closed.md)
measures.

Two clauses of the body are unbuilt. The stage headers are deferred into
[a-stage-header-groups-cards-by-nothing-the-tree-declares.md](a-stage-header-groups-cards-by-nothing-the-tree-declares.md)
on a ruling neither a worker nor a review may make, with its own red criterion
— so `done` here rather than `open`, on the
[findings/loop/2026.08.07-the-review-prompt-has-no-path-for-a-partial-deferral.md](../findings/loop/2026.08.07-the-review-prompt-has-no-path-for-a-partial-deferral.md)
precedent: reopening would serve a run a criterion that is already green. The
plots clause was dropped without being named, and is folded into
[the-pinned-step-holds-the-slot-under-the-canvas.md](the-pinned-step-holds-the-slot-under-the-canvas.md),
which owns the sentence it collides with.
