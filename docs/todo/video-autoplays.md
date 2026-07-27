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
- After the neighbour-project modal resolves, if one is going to be shown —
  `main_window.py:536-543` asks about an adjacent project on open, and a video
  playing behind a modal is a worse first second than a still one.

`_on_editor_open_changed` (`main_window.py:696-707`) gates `_play_action` on
`self._player.metadata is not None`, so the same "is there a video" condition
is already written down; use it rather than inventing a second test.

1–5 lines. One test: opening a source leaves the player playing, and it does so
after the open completes rather than before.

Note in passing: if the **No save prompts, keep history** item
(`docs/todo/no-save-prompts-keep-history.md`) removes the open-time modals,
the second constraint above disappears and this gets simpler, not harder — so
there is no reason to wait for it.
