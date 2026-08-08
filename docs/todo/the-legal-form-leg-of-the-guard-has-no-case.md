---
title: The guard's legal-form leg is the one of the three still carried by no subject
priority: normal
phase: "00"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest \"tests/docs/test_doc_index.py::test_a_template_that_shows_only_the_failing_form_is_reported\" -q"
opened: 2026-08-07
---

# The guard's legal-form leg is the one of the three still carried by no subject

`_silent` in `tests/docs/test_doc_index.py` now reads three counts for presence,
`shown.stated and shown.legal and shown.illegal`. Deleting `shown.legal` from
that conjunction leaves the whole module at 81 passed. The same deletion against
`5ba6b66`'s tuple form leaves it at 80 passed, so this is not something `6d81fde`
introduced — it is the leg the run of items that closed the other two never
reached.

Each surviving subject fails a leg that is not this one. `SILENT_TEMPLATE` is
`(1, 0, 0)` and so fails `legal` and `illegal` together; `ONE_FORM_TEMPLATE` is
`(1, 1, 0)`, which is the *illegal* leg's case; `UNSTATED_TEMPLATE` is `(0, 1, 1)`
and is `stated`'s. Nothing anywhere is `(1, 0, 1)` — a template that states the
rule and shows the form that fails without ever offering the one that works. That
is the mirror of the half-taught state `ONE_FORM_TEMPLATE` exists for, and the
shape a template reaches by trimming the fix as redundant with the sentence above
it rather than by trimming the example that reads like a mistake.

The fixture that closes this already exists in the same sense the last two did:
`_docs_with_template` builds the tree, so the cost is one more template constant
plus its assertion. `SILENT_TEMPLATE` with the illegal example appended is the
subject, and `["questions: states it 1x, 0 legal / 1 illegal"]` is what the guard
should say about it.

Coverage of a guard, not a defect in one — the three real templates show both
forms and the guard's answer about them is right today.
