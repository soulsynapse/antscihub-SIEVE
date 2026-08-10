"""The views: what stands in a pane, one folder each.

A view is the occupant and never the space (ADR-0001), so nothing here may name
a pane, a side or a swipe position — a view that reached for `window.right`
would be a view that could only be housed in one place, which is the one thing
the panes were built not to require. What a view knows about where it stands is
its own size, and the frame is what decides that.

One folder per view rather than one module, because a view arrives as a surface
and not a widget: the list, the card it repeats, and the record it reads are
each worth reading alone, and keeping them together is what stops the next view
from importing the middle of this one.
"""
