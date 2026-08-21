---
title: The right pane swipes between positions
group: Layer 1
position: 3
status: settled
decided: 2026-08-10
---

The right pane holds its three screens — the project, the pipeline, the walked step — as positions on one track, in that order, and moves between them by sliding the track. They are positions and not panes: the pane is the space and stays one space, and ← and → are spent on walking the track.

Three panes standing at once is what this refuses. The three are never read
against each other — they are read against the footage on the left, one at a
time — so a frame that showed all three would be taking room from the canvas to
show two screens nobody is looking at, on the axis the user is already trading
by hand at the splitter. Stacking them in place with no motion refuses the same
cost and buys a different one: three lookalike screens in the same rectangle,
with nothing but their contents to say which is up.

The slide is what pays for that. Direction of travel is the cheapest available
statement of where you now are relative to where you were, it costs no pixels,
and it costs no layout — the pane never changes size, so nothing inside a
position is re-laid out on the way past. The order carries the rest: the project
you opened, the chain in it, the step you are standing on in that chain, so out
and in are directions in the work rather than a mapping to remember.

They are positions and not panes because the frame's panes are countable and
fixed, which is what makes every claim in [ADR-0001](ADR-0001-panes-house-any-view.md)
and [ADR-0002](ADR-0002-a-subpane-divides-the-spare-axis.md) checkable — which
pane houses a view, which sides it anchors a subpane to, what a resize does to
it. A swipe adds none of that: it is a view in the right pane, so the right pane
still anchors its two sides and still answers a resize the way it did, and a
fourth screen added to the track changes nothing about the frame. The track is
moved rather than the positions for the same reason a subpane is a fixed extent
— one animated number, and every position keeps the geometry it was handed.

The keys are the corollary. A track is a line, so the two keys that mean *along
a line* are the ones that walk it, and they are spent on it frame-wide rather
than re-bound per position; ↑ and ↓ stay unbound, held for whatever selection
the position in view owns. Clamped at the ends and not wrapped: a wrap would put
the user at the far end of the work with the slide saying they had walked one
step further into it.

The track takes that axis last rather than first, which is the clause the
positions did not need and the shapes inside them do. A tab row and a segmented
bar run on a line of their own, and a user who has put the keyboard on one is
looking straight at the line they mean; the track is the line they are standing
*in*, which is the further of the two. So a widget that claims ← or → gets it,
and the track answers only where nothing nearer did. It is still one motion
spelled one way — the alternative is a modifier, which would buy the track a
vocabulary item it needs nowhere else in order to settle two widgets.
