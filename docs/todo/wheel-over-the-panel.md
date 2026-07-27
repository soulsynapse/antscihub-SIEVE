---
title: Wheel over the panel
status: open
opened: 2026-07-27
gated_on: >
  nothing structurally — but it compounds: param_form generates knobs for every
  future filter, so fixing it per-widget later means touching every card
reads:
  - src/sieve/gui/wheel_steps.py
  - src/sieve/gui/param_form.py
---

# Wheel over the panel

Noticed `<=2026.07.27`: scrolling the filter panel to reach a control below
also nudges whatever knob the cursor passed over — rescale jumps, normalize
flips, block size changes.

This is not a near-miss in a scroll area; it is guaranteed.
`WheelSteps.eventFilter` (`src/sieve/gui/wheel_steps.py:71-97`) is installed on
the `QApplication`, matches any `QAbstractSlider` or `QAbstractSpinBox`, steps
it, and returns `True` unconditionally — with the comment at lines 95–97 saying
why it consumes even a partial trackpad delta. There is no focus test and no
path by which the wheel reaches the scroll area's viewport. The panel can never
be scrolled past a control.

The filter is otherwise correct and worth keeping: one detent is one
`singleStep` everywhere, runs accelerate, trackpad fractions accumulate. The
change is a precondition, not a rewrite — act only when the control is the
intended target, and let the event through otherwise. The usual rule is
"the widget has focus"; a click-to-focus knob then steps, and an unfocused one
scrolls the panel. Whatever rule is chosen, the accumulator (`_residual`,
`_run`, `_target`) must not be advanced on events that are passed through, or a
scroll past a knob will poison the next real gesture on it.

Fix it here, in one place. `param_form.py` generates spin boxes and sliders for
every filter's parameters, so a per-widget `setFocusPolicy` /
`installEventFilter` fix would have to be repeated on every card that exists
and every card added afterwards. That is the compounding part.

~15–30 lines. Tests: a wheel over an unfocused spin box leaves its value alone
and is not consumed; a wheel over a focused one still steps by exactly one; and
a pass-through does not disturb the acceleration run on a subsequent focused
gesture.

Downstream: this is also the trigger for the **Band power at small block size**
item (`docs/todo/band-power-at-small-block-size.md`) — one accidental notch on
the Block spin box is what puts the detector into the state that hangs.
