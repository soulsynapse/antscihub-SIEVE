---
title: A generated control commits on intent, and a value passed through is not one
priority: normal
phase: "7"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/gui/test_param_generator.py -q -k 'a_wheel_over_a_control_does_not_edit_the_document or arrowing_a_closed_choice_commits_once'"
opened: 2026-08-08
---

# A generated control commits on intent, and a value passed through is not one

Every value a control emits is a re-plan, a new cache key and a render, so the
question of *when* a widget has been edited is a product question rather than a
Qt detail — and it is the one thing v2 learned about widgets that 07.5's
generator did not bring over. Two of its cases are live in `gui/param_form.py`
today: a wheel over the panel steps every spin box and combo it passes,
committing each notch; and `QComboBox.activated`, which the generator wires,
fires for arrow keys on a *closed* combo, so holding Down through a tool's mode
list commits every mode on the way past.

v2's answers are `gui/wheel_steps.py` and `gui/commit_combo.py`, and both are
"everything else under `gui/`" in PLAN.md's port disposition — re-derived, not
ported. The second is the one with a decision in it: v2 removed the arrow case
rather than filtering it, by making navigation keys open the popup, where
highlighting and selecting are distinct states. That is a rule about what a
control *is*, so it belongs to the generator that mints every control rather
than to a widget written later beside it.

Nothing in the tree distinguishes the two signals today, which is worth knowing
before the arrow case is written: swapping `activated` for `currentIndexChanged`
survives all of `tests/gui/test_param_generator.py` (review of `b19599f`). The
reason is that `_enum` sets the index *before* it connects, so the construction
claim — building a form is not an edit — is carried by the ordering rather than
by the signal, and the choice of signal is unpinned until a case exercises a
closed combo under arrow keys. A mutant that deletes a connection proves the
wiring exists; only one that swaps it proves the choice.

While that control is open: `_scalar_range`'s comment calls its single step "a
tenth of the range", and the value is `0.05` on a range of `1.0`. One of the two
is wrong and the comment is the likelier.

The scalar half has a third case v2 states and this tree cannot yet: an edit
runs from the first keystroke to a commit, and nothing in between reaches the
document. `QSpinBox.valueChanged` fires per keystroke, so typing `120` into a
frame count commits `1`, then `12`, then `120` — three plans, two of them for
values the user was in the middle of typing. Whether that is `editingFinished`
or v2's own answer is this item's to settle; the loop budget is what makes it a
real cost rather than a tidiness argument, since each of those is a preview.

## The render each of those values costs is synchronous on the GUI thread (2026-08-08, from 07.11)

07.11 wired the loop, and the cost this item argues about is now real rather
than prospective: `gui/tuning.py` renders the working window on the GUI thread,
synchronously, on the turn after an edit lands. Every pass-through value the
cases above describe — three plans for a typed `120`, one per mode for a held
Down key — is a whole window render, and the window is frozen for each of them.

Two things keep that inside VISION's promise today and neither is the fix. A
single-shot `QTimer` restarted per request collapses the edits that arrive
within one turn of the event loop into one render, which is coalescing for a
burst and not for a sequence of committed values; and the reference workload
renders in ~5 ms
(`findings/2026.08.08-the-loop-budget-is-met-through-the-gui.md`), so nothing
freezes perceptibly on the fixture. On footage the scope note does not cover,
each pass-through value is a visible stall — which is what makes the two cases
above a product question rather than a tidiness one, and is the sentence this
item's `done_when` does not yet reach.

Moving the render off the GUI thread is deliberately *not* folded in here.
`pipeline/preview.py` says coalescing belongs to the transport layer and that a
caller rendering on a worker must hold one render in flight and one pending;
that is a mechanism with a fence in it, and it is worth doing after the number
of renders is right rather than as a way of hiding how many there are.

## The signal swap this item predicted a case would pin is equivalent instead (2026-08-08)

All three cases are answered in `gui/param_form.py` and the two above are the
`done_when`'s. The prediction in the paragraph above them did not hold:
`findings/2026.08.08-removing-the-arrow-case-makes-the-combos-signal-choice-unpinnable-rather-than-pinned.md`
measures `activated ==> currentIndexChanged` surviving still, now because a
closed combo has no arrow behaviour left for the two signals to disagree about.
The other four rules die under the sweep.
