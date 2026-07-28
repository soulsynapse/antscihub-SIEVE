---
title: Video autoplays
status: open
opened: 2026-07-27
gated_on: nothing structurally — the smallest item in the folder
reads:
  - src/sieve/gui/player.py
  - src/sieve/gui/main_window.py
---

# Video autoplays

Noticed `<=2026.07.27`: an opened video should start playing.

Nothing ever calls `VideoPlayer.play` (`src/sieve/gui/player.py:235`) except
the toggle at `player.py:262`. There is no autoplay path to repair — there is
none at all.

Placement is the whole decision, and there are two constraints:

- After the document has bound to the source, so the first frames are not
  racing the open.
- ~~After the neighbour-project modal resolves~~ — **dissolved 2026-07-27.**
  `docs/todo/no-save-prompts-keep-history.md` settled that the neighbour project
  is opened and announced in the status bar rather than asked about, so there is
  no modal left for a playing video to sit behind. If that item lands first,
  this constraint is already gone; if this one lands first, `:536-543` is still
  a modal and the ordering still holds. Either way it only gets simpler.

`_on_editor_open_changed` (`main_window.py:696-707`) gates `_play_action` on
`self._player.metadata is not None`, so the same "is there a video" condition
is already written down; use it rather than inventing a second test.

1–5 lines. One test: opening a source leaves the player playing, and it does so
after the open completes rather than before.
