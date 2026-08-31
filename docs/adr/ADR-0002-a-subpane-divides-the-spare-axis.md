---
title: A subpane divides its pane's spare axis
group: Layer 1
position: 2
status: settled
decided: 2026-08-10
---

A pane offers a subpane only the axis its own outer boundary left alone: the top and bottom sides in the left and right panes, which sit either side of a vertical splitter, and the left and right sides in the bottom pane, which runs full width under both. Both axes in one pane is refused, not nested; further cuts on the one axis are not.

Offering all four sides everywhere costs a decision the frame has no reason to
make: with a top strip and a left strip in the same pane, one of them owns the
corner, and whichever answer is wired in is arbitrary and then permanent. Taking
the spare axis instead means every cut in a pane runs the full width or height
of it and no strip ever meets another at a corner, so a side can stack more than
one without reopening the question the axis already answered. The core keeps
whatever the cuts leave, which is what caps the stack: the strips are a fixed
extent and the pane is not, so a side that took any number of them could leave
the core the smallest thing in its own pane.

The strip is a fixed extent along the axis it anchors on, like the bottom pane's
height and unlike the left-against-right splitter. A boundary is the user's
to drag when the trade is theirs to make; the space a subpane takes is not that
trade — a strip draggable until it swallowed the core would stop being the
smaller pane anchored to a side, which is the whole of what a subpane is. See
[ADR-0001](ADR-0001-panes-house-any-view.md): a subpane is a pane, so it houses
any view on the same terms, clipping included.

## Rejected

`QMainWindow::setCorner(Qt::Corner, Qt::DockWidgetArea)` cautionary tale: Qt
lets all four sides dock everywhere, meets the corner problem this refuses,
and answers it by making corner ownership a setting — so the arbitrary
decision is not avoided, it is deferred onto every application and then
frozen there. A layout that never lets two strips meet has no corner to
assign.
