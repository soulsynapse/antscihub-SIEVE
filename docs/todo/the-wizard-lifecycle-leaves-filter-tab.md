---
title: The wizard lifecycle leaves filter_tab
status: open
opened: 2026-08-05T22:46:31-07:00
priority: normal
gated_on: >
  nothing structurally — but `filter-tab-is-eleven-jobs` judges this slice
  cheaper after `detector-state-dies`, and that judgement stands
after: [filter-tab-is-eleven-jobs]
reads:
  - src/sieve/gui/filter_tab.py
  - src/sieve/gui/wizard_model.py
  - src/sieve/gui/wizard.py
  - tests/gui/test_wizard.py
---

# The wizard lifecycle leaves filter_tab

Slice 2 of `filter-tab-is-eleven-jobs`, taken as its own item because that item
says the unit is one named responsibility and one commit, and because slices 1
and 3 already went out that way — `the-source-boundary-is-its-own-object`
landed, `the-band-handlers-are-one-shape-said-five-times` is deferred with its
trigger. This is the third of the three, and the parent item is explicit that
"split filter_tab" is not a specification while each numbered slice is.

The methods: `_open_wizard`, `_on_chain_proposed`, `_on_hover_preview`,
`_on_hover_ended`, `_on_wizard_accepted`, `_on_wizard_cancelled`,
`_close_wizard`, `wizard`. Roughly 150 lines, and `gui/wizard_model.py` is
already the state half waiting for it.

**What makes this slice harder than the one that succeeded, and it is not
size.** Git says nothing either way: `wizard.py` and `wizard_model.py` have
never changed without `filter_tab.py`, so the wizard lifecycle has never earned
its own commit. The source boundary had three commits sitting 85–92% inside its
section, which is why it was the slice with evidence and why it went first.
This one has none, so it rests entirely on the seam test rather than on
history — and history is the thing that has been right twice here.

**The seam test, applied before writing code:** name the signals that cross it.
If the extracted object must hold a back-reference to the tab to do its job, the
seam is wrong, and the right move is to route through the document or emit a
signal the tab connects — never to pass `self`. The source boundary passed at
three signals with no back-reference; that is the bar.

**Done looks like** the wizard's lifecycle owned by one object that the tab
wires and does not reach into, `tests/gui/test_wizard.py` still passing, and the
crossing signals nameable in one sentence. **What must not happen** is two files
that each need the other: the coupling here is Qt signal wiring, invisible to
both gates — a `connect()` call is equally well-typed whichever object it lands
on, and `.importlinter` sees nothing because it is all one package — so
`tests/gui/test_filter_tab.py` passes throughout a bad split. That is the whole
reason the parent item refuses to be taken at once.

One ordering note carried from the parent: this judgement is cheaper made after
`detector-state-dies`, because the jobs reaching into `chain_model` and
`detector_worker` internals shrink to signal wiring once that lands. The item is
open rather than deferred because the wizard slice does not itself touch those
internals — but if the seam looks ambiguous when you get here, that is the
reason to wait rather than to guess.
