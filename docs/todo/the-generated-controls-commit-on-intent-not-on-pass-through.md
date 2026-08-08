---
title: A generated control commits on intent, and a value passed through is not one
priority: normal
phase: "7"
status: open
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
