---
title: Spacebar dies on focus
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but the announce-my-focus pattern is already copied
  twice, so every new typing control copies it again
reads:
  - src/sieve/gui/main_window.py
  - src/sieve/gui/crop_tools.py
  - src/sieve/gui/replicate_tab.py
---

# Spacebar dies on focus

Noticed `<=2026.07.27`: after touching a drop menu or a field, spacebar stops
starting playback and never comes back.

`MainWindow._on_editor_open_changed` (`src/sieve/gui/main_window.py:696-707`)
is a plain boolean latch. It disables play, delete, mark-in and mark-out while
"an editor is open" — correct in intent (rule 6's mirror direction: a control
must not look more live than it is; a rename typed into the table would mark a
clip once per vowel). The defect is that it is not reference-counted while
being fed by two independent sources:

- `replicate_tab.py:191-192` — the table delegate's `editing_started` /
  `editing_finished`.
- `crop_tools.py:220` — `field.focus_changed`, forwarded through
  `replicate_tab.py:181`. This is *plain focus* on the crop-tools number
  fields, not an open cell editor.

Both funnel into one `bool` at `main_window.py:295`. Any interleaving where a
`False` arrives before a still-outstanding `True` — or where a `FocusOut` is
never delivered because the widget was hidden, reparented, or the panel
collapsed while focused — leaves `editing` stuck true and play disabled for the
rest of the session. There is no path that re-enables it except another
editor closing cleanly.

Two things to fix, and the second is the one that matters:

1. Make the latch a counter, or better, a set of the currently-editing
   sources, so a stale `False` cannot clear a live `True` and a source that
   disappears can be dropped by identity rather than by decrement.
2. Focus alone must not suppress playback — see the decision below.

Recovery matters as much as prevention: whatever the model, there must be a
point at which it is known-good — the window losing activation, or the tab
changing — so a stuck state cannot outlive one gesture.

## Decided 2026.07.27: suppression follows the commit, not the focus

**Spacebar plays unless something is actively being edited.** A spin box holding
focus is not an editor; suppressing on plain focus is what makes the stuck state
reachable by clicking around, and it is the behaviour to remove, not merely to
make robust. So `crop_tools.py:220`'s `field.focus_changed` stops being a
suppression source; the table delegate's `editing_started` / `editing_finished`
(`replicate_tab.py:191-192`) stays one.

*Rejected side:* keeping focus-based suppression and only fixing the latch —
smaller, and it preserves a behaviour nobody wants once it is named.

**An edit ends at a commit, and the commit restores playback.** Enter commits,
Esc cancels, clicking out commits; each of the three returns spacebar. This is
what makes "actively editing" a state with a defined exit rather than a focus
flag that can be stranded — the recovery requirement above is then satisfied by
construction rather than by a rescue hook.

**The field's *value* follows the same boundary, which is the part that reaches
beyond this item.** A number field applies on commit, not per keystroke: typing
`15` into a field showing `9` must not apply `1` on the way. And a drop menu
applies on *selection*, not on highlight — arrowing through a combo box must not
retune once per row. Both are the same rule (a control's value changes when the
user says it does), and both are behaviour changes to the crop-tools fields and
the chain menus rather than to the play latch. If they do not fit alongside the
latch fix, split them out as one item — they belong together and neither belongs
with the counter.

~20–40 lines for the latch and the focus-source removal; the commit-boundary
work is larger and unmeasured.

Tests: two overlapping editors, the second closing first, leaves play enabled
only when both are done; a focused field destroyed or hidden without `FocusOut`
does not leave play disabled; clicking a crop-tools number field without typing
leaves spacebar working; Enter, Esc and click-out each restore it from an active
edit; typing into a table cell still does not mark a clip; and a partially typed
number never reaches the document.
