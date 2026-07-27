---
title: The bottom bar that went missing
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but the first step is archaeology, not code: find the
  commit that removed it before deciding what to restore
reads:
  - src/sieve/gui/timeline_bar.py
  - src/sieve/gui/main_window.py
  - src/sieve/gui/replicate_tab.py
---

# The bottom bar that went missing

Noticed `<=2026.07.27`: "we had a beautiful bottom bar previously but it's now
gone."

**This item is the least well specified of the bundle and the first step is to
find out what it refers to.** Two candidates exist in the tree and neither is
obviously absent:

- `gui/timeline_bar.py` — "the anchor: one full-width band across the bottom of
  the window" (module docstring, `:1`). `replicate_tab.py:15` says the scrub bar
  and the clip editor are both this one widget, one band across the bottom.
- `MainWindow.statusBar()` — used at `main_window.py:144, 307, 348, 521, 565,
  584, 602, 619, 657, 672, 676`. Very much alive.

So "gone" means either a third thing that was deleted, or one of these two
losing a feature, styling, or a placement rather than being removed. Resolve it
with `git log -p -- src/sieve/gui/` around the layout changes rather than by
guessing; the completed-todo entries for the filter-tab work are the likeliest
window. If it turns out to be styling that regressed rather than a widget that
vanished, this becomes a much smaller item and should be rescoped in place.

Until that is known, no line estimate here would mean anything, and writing one
would make this look better-founded than it is.

One constraint to carry in: whatever is restored has to survive the layout the
filter tab now imposes (`filter_tab.py:_build_layout`, `:295-313`), which owns
the bottom of its own left column with the count plot, the D row, and the HUD.
A window-level bar and a tab-level footer are different things, and the
original may have been either.
