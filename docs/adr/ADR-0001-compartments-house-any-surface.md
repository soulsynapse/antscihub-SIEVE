---
title: A compartment houses any surface
status: settled
decided: 2026-08-10
---

A compartment constrains geometry and nothing else, so any surface may stand
in any of the three. The frame does not know which surface it is holding, and
no surface names the compartment it belongs in; the placement is the user's,
and every one of them is legal.

Why: this is where coarse-grained customization is bought, once, in the frame,
instead of per surface forever. The alternative — a compartment declaring the
surfaces it accepts — makes each new surface an edit to the frame and each
rearrangement a negotiation between the two, and the set of legal layouts then
has to be written down somewhere and kept true. Under this decision there is
nothing to keep true: the layout is a placement of surfaces into rooms, and
the frame's own claims stay the ones it can check — which boundary drags,
which is fixed, what resizing does (`src/sieve/gui/frame/window.py`).

The cost is taken deliberately. A surface in a compartment shaped wrong for it
will be cramped, clipped, or ugly, and the frame will not stop the user from
putting it there. That is the price of the property, not a defect to be
designed out: refusing a placement to protect the user from an ugly one is the
same edit as the compartment knowing its contents, and it costs the same
thing. A surface that cannot survive a bad compartment is a fault in the
surface — everything it draws is drawn against the room it was given
(`Blank` in `src/sieve/gui/frame/compartments.py`, which holds a layout and an
expanding size policy and nothing about what fills it; the three builders
differ only in minimum width and fixed height).

What this does not decide: the compartments themselves. Three rooms, their
boundaries, and their kinds are fixed by the frame. Splitting one, floating a
surface out of the window, or stacking two in one room are all outside this
decision, and none of them is implied by it.
