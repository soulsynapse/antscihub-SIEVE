---
title: Right click back to the replicate tab
status: deferred
opened: 2026-07-27
gated_on: >
  the click-through-navigation decision going the other way — that item
  explicitly rejected a right-click binding in favour of an output boundary in
  the chain-stack, so building this now knowingly contradicts it
reads:
  - docs/todo/click-through-navigation.md
  - src/sieve/gui/composite_view.py
  - src/sieve/gui/filter_tab.py
---

# Right click back to the replicate tab

Noticed `<=2026.07.27`: "right click on the video in the filter tab should take
it back to the replicate tab full view."

Mechanically this is small — `_CompositePane.mousePressEvent`
(`composite_view.py:202`) already handles presses, and the tab switch is a
signal out of `StepCompositeView` to the window.

**It is deferred because it is a decision already taken the other way, not
because it is hard.** `docs/todo/click-through-navigation.md` argues that the
gesture back out of a filtered view belongs to an output boundary in the
chain-stack, and rejects a right-click binding specifically. Building this now
would put a second, undocumented navigation affordance on the same surface, and
the two would have to be reconciled the first time either moved. Rule 1's
spirit applies to gestures as much as to execution: one path.

The trigger is therefore a decision, not an event — either the click-through
item revisits its rejection (a right-click *plus* the boundary is defensible if
they mean the same thing), or the boundary lands and this item is closed by it
rather than built.

If it is built anyway as a knowingly provisional stopgap — which is a
legitimate call the user can make — say so in the completed entry, because a
provisional binding that is not labelled as provisional is what makes the later
reconciliation expensive. It should also land *after*
`docs/todo/zoom-on-the-composite-view.md`, for the same hit-testing reason the
other two composite-view items carry.

Constraint worth recording now: "back to the full view" has to define what
happens to the current selection and window. Returning to the replicate tab
without carrying the selected replicate is a different gesture from the one the
user is asking for, and the difference is invisible until someone has two
replicates.
