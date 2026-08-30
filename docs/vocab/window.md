---
title: window
group: Layer 1
position: 1
gloss: The application — the one top-level frame, holding a menu bar, the panes, and the boundaries between them. There is exactly one, and nothing else divides into panes.
origin: decided
defined: 2026-08-10
---

The application — the one top-level frame, holding a menu bar, the panes, and
the boundaries between them. There is exactly one, and nothing else divides
into panes: a thing that showed panes of its own would be a second window and
the word would stop counting.

## Where it lives

`gui/frame/window.py` is the window itself; `gui/frame/chrome.py` styles the
bar it carries. The boundaries are the window's own and not a pane's — a
splitter left to right, a fixed seam above the bottom.
