---
title: pane
group: Layer 1
position: 2
gloss: A compartment the window divides into — a region with a boundary, a size policy and a name, holding whatever is put in it. The space, never its occupant.
origin: decided
defined: 2026-08-10
---

A compartment the window divides into: a region with a boundary, a size policy
and a name, holding whatever is put in it. A pane is the space, never its
occupant — it stays a pane while empty, and swapping what stands in it does not
make it a different pane. Panes are named for position and not for content,
which is what keeps them countable; see [view](view.md) for the occupant and
[swipe](swipe.md) for the construct that adds screens without adding panes.

## Where it lives

`gui/frame/panes.py` holds the three and the sides a [subpane](subpane.md) may
anchor to in each. They are laid out before anything stands in them, so the
frame's layout claims are checkable against an empty window.
