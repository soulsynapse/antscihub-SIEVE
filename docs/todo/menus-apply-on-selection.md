---
title: A drop menu applies on selection, not on highlight
status: open
opened: 2026-07-27
gated_on: >
  nothing — rule and mechanism are both decided (2026-07-27, below): arrow
  keys open the popup, and `textActivated` is the one commit signal
reads:
  - src/sieve/gui/param_form.py
  - src/sieve/gui/filter_tab.py
  - docs/completed-todo/2026.07.27-spacebar-dies-on-focus.md
---

# A drop menu applies on selection, not on highlight

Split out of `spacebar-dies-on-focus` on 2026-07-27, which decided the rule and
built the half of it that lives in number fields. The rule is one sentence: **a
control's value changes when the user says it does.** The number fields now
commit on Enter, Esc, or leaving the field, and nothing in between reaches the
document. The combo boxes still change on every index they pass through.

Two of them:

- `param_form.py:78` — `combo.currentTextChanged` on the generated enum widget.
  This is a *filter parameter*, so every row arrowed past is a re-plan, a new
  cache key, and a render.
- `filter_tab.py:347` — `self._normalize.currentTextChanged`, the composite's
  normalisation mode. Cheaper, but the same gesture.

Arrowing from `none` to `per_frame` through `per_block` retunes on `per_block`
on the way past. With a filter parameter that is a full re-render of the working
window for a value the user never chose, and it happens at whatever speed they
hold the arrow key down at.

## What makes this its own item

Swapping the signal is not the fix, and that is the whole reason it did not ride
along with the number fields. `QComboBox` emits `activated` — the "user chose
this" signal — for **keyboard navigation of a closed combo box** as well as for
a click in the popup, because Qt considers arrowing a closed combo an act of
selection. So `currentTextChanged` → `textActivated` removes the popup-highlight
case and leaves the arrow-key case exactly as it is.

**Decided 2026-07-27: option (1).** Arrow keys on a closed combo open the
popup instead of stepping the value; inside the popup, arrowing highlights
and only Enter or a click selects, so `textActivated` becomes a complete
statement of "the user chose this" and is the only signal wired to the
document. This makes highlight and selection distinct states everywhere,
which is the number fields' rule restated for a different widget, with no
pending-value display to invent. *Rejected sides:* (2) debounce — makes
"chosen" a function of how fast the user moves, the per-keystroke defect in
new clothes; (3) pending-and-commit — consistent but the most work, and its
pending state must be visibly distinct or it breaks rule 6's mirror clause,
a cost (1) simply does not incur. The measurement below is worth taking
anyway, but as a finding about cache behaviour, not as this item's gate —
even a fully cache-served pass-through value is a wasted render queued in
front of the one the user wants.

The options as originally weighed, kept for the record:

1. **Open the popup on arrow keys** instead of stepping the closed combo, so
   there is a highlight state to be distinct from a selection. Qt has
   `QComboBox` policies near this but not this; it is an event filter.
2. **Debounce the apply** — a value that survives ~200 ms is the chosen one.
   Cheap, and wrong in the same way per-keystroke was: it makes "chosen" a
   function of how fast the user moves.
3. **Take the number fields' shape literally**: the combo announces a *pending*
   value and commits on Enter, click, or focus-out. Consistent, and the most
   work — it also needs the pending state to be visible, or rule 6's mirror
   direction is broken (a control showing `per_block` while the pipeline runs
   `none` looks more live than it is).

There is a fourth possibility worth measuring before choosing: if a re-plan on a
value the user passes through is fully served from cache on the way back, the
cost is a wasted render and not a wrong result, and (1) is enough. That is a
`docs/findings/` measurement, not an assumption.

Tests: arrowing a closed combo from the first entry to the third applies the
third and not the second; clicking an entry in the popup applies it; the value
the pipeline ran and the value the widget shows are never different at rest.
