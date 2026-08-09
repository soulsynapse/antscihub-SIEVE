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

## 2026-08-09 (review): whether a card ever draws a plot is this item's to say

09.1's body asked for "title, knobs, and plots on the card". It shipped title
and knobs; the cards draw no plots and the run's account does not mention the
clause
([findings/loop/2026.08.09-a-loud-deferral-covers-for-a-silent-one-in-the-same-sentence.md](../findings/loop/2026.08.09-a-loud-deferral-covers-for-a-silent-one-in-the-same-sentence.md)).
Dropping it was right and the reason is this item's sentence: MOCKUP-MAP.md's
only row joining plots to a card is "The pinned step", and it says the card
*says where its surface went* instead of drawing plots twice. So the clause
09.1 left behind is not owed by 09.1 — it is the negative half of what this
item builds, and this item is where it gets stated: a card carries a note, not
a plot, and the note is what `NO_SURFACE_NOTE` is for on the steps that have no
surface at all.

`done_when` (`-k pinned_slot`) was written before this and is not widened here.
A case that asserts a card holds no `GraphPanel` — that the "says where it
went" half is a note rather than a second drawing — would be the part of this
paragraph a criterion can reach.
