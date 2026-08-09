---
title: The pinned step holds the slot under the canvas
step: "09.3"
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k pinned_slot"
opened: 2026-08-09
---

# The pinned step holds the slot under the canvas

One step is held under the canvas at full width — detection by default, any
step the user pins instead, one slot so pinning evicts. The slot re-fits to
the natural height the pinned step asks for rather than splitting the window
by thirds; the step's card in the stack says where its surface went instead
of drawing plots twice; a step with no plots states its surface in words. P
pins the current step. MOCKUP-MAP.md rows "The pinned step" and "Hotkeys" —
`PinnedStep`, `MockWindow._fit_pin`, `_pin_button`, `NO_SURFACE_NOTE`,
`PINNED_DEFAULT` in the referent. The pin is view state, not a param: it
lives GUI-side and never touches the document.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k pinned_slot
    119 deselected in 0.68s
    exit: 5
