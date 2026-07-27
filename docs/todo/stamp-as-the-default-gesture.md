---
title: Stamp as the default gesture
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but build it after `docs/todo/ratio-wrong-after-undo.md`,
  because it leans on selection and replicate signals firing reliably
reads:
  - src/sieve/gui/video_view.py
  - src/sieve/gui/crop_tools.py
  - src/sieve/gui/replicate_tab.py
---

# Stamp as the default gesture

Noticed `<=2026.07.27`: "stamp should be the default once one is drawn. Stamp
should be the default if the user clicks, and if the user tries to drag click
it should let it draw. It should stamp based on the highlighted replicate."

Three claims, and they are in three different states.

**The click-versus-drag half already works.** `video_view.py:586-632`: a
release that travelled finishes as a region and sets the stamp size in *both*
modes (`:617-623`, with the comment explaining that requiring a mode switch
before the defining draw is backwards); a release that travelled nowhere is
`_clicked`, which stamps on empty space when the mode is `STAMP` and a size
exists (`:627-632`), and selects otherwise. Drags draw even in stamp mode
today. Nothing to build here — confirm it and say so.

**"Default once one is drawn" is a mode-ownership problem.** The mode is a
one-way panel→view toggle: `CropTools.mode_changed`
(`crop_tools.py:78`, emitted at `:327`) → `ReplicateTab._on_mode_changed`
(`replicate_tab.py:283-285`) → `VideoView.set_mode`. There are two owners of
the same state and no back-channel, so the view cannot flip itself to `STAMP`
after a draw without the panel's radio buttons going stale — and a toggle
showing "draw" while clicks stamp is rule 6's mirror direction exactly (a
control must never look more live, or more truthful, than it is). Either the
view gains a `mode_changed` signal the panel follows, or the mode moves to one
owner and both widgets become views over it. Prefer the second; it is the same
shape as `ReplicateDocument` being the one store for tuning.

**"Stamp based on the highlighted replicate" is not implemented at all.**
`_stamp_size` (`video_view.py:187`, set at `:257` and `:622`) is a remembered
`(width, height)` from the last draw or the last panel edit. It has no relation
to the selected replicate's ROI. Making the stamp track the selection means
reading the selected replicate's geometry, which is why this item goes after
`docs/todo/ratio-wrong-after-undo.md` — until `replicate_changed` reaches the
places that need it and `select` is settled, "the highlighted replicate's size"
is a value that can silently be one edit stale.

Do not re-derive placement: `ROI.placed_in` (`core/types.py`) is the slide rule
a stamp uses at the frame edge, `clamped_to` is the other rule and trims, and
`docs/TODO.md`'s settled table says reaching for the wrong one makes a rack
non-uniform while every number on screen says it worked.

Tests: a completed draw leaves the panel toggle and the view agreeing on
`STAMP`; a click after that stamps at the selected replicate's size, not the
last drawn one; and a drag in stamp mode still draws.
