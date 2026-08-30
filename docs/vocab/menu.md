---
title: menu
group: Layer 1
position: 5
gloss: The drop menu at the top of the window — the bar, and what the window itself can be asked to do.
origin: decided
defined: 2026-08-10
---

The drop menu at the top of the window: the bar, and what the window itself can
be asked to do. It belongs to the [window](window.md) and not to any
[pane](pane.md), which is what decides whether a verb goes on it — a verb about
what is currently in a pane does not.

## Where it lives

`gui/frame/menu.py` is the bar and its verbs; `gui/primitives/menu.py` is the
styled popup they drop. A title whose whole content is one verb is a plain
action on the bar rather than a one-entry drop.
