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
2. Decide whether *focus* on a number field should suppress playback at all.
   A spin box that has focus but is not being typed into is not an editor;
   suppressing on focus is what makes the failure reachable by clicking around.

Recovery matters as much as prevention: whatever the model, there must be a
point at which it is known-good — the window losing activation, or the tab
changing — so a stuck state cannot outlive one gesture.

~20–40 lines. Tests: two overlapping editors, the second closing first, leaves
play enabled only when both are done; a focused field destroyed or hidden
without `FocusOut` does not leave play disabled; and typing into a table cell
still does not mark a clip.
