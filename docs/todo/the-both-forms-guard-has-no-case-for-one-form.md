---
title: The guard's "both forms" is a conjunction no subject has ever tested one leg of
priority: normal
phase: "00"
status: done
gated_on: nothing
done_when: "uv run pytest \"tests/docs/test_doc_index.py::test_a_template_that_shows_one_form_is_reported\" -q"
opened: 2026-08-07
---

# The guard's "both forms" is a conjunction no subject has ever tested one leg of

`_silent` in `tests/docs/test_doc_index.py` reports a template whose
`(stated, bool(legal), bool(illegal))` is not `(1, True, True)`. Three claims,
and every subject the guard has ever run over sits at one of the two poles: the
three real templates satisfy all three, and the synthetic `SILENT_TEMPLATE` that
`a37422d` added fails two of them at once by showing nothing at all. Nothing in
the tree or the fixture shows one form and not the other, and nothing states the
rule twice.

Two mutants confirm it. Dropping the `stated` element from the tuple entirely,
and weakening the conjunction to `bool(legal) or bool(illegal)`, both survive the
whole of `tests/docs/test_doc_index.py`. The second is the one that matters: under
it a template offering the fix and never showing the failing form passes, and that
is precisely the half-taught state the guard's own docstring says an author must
not be handed.

The fixture that closes this already exists — `a37422d` built a docs tree the
guard has never been told about, so the cost is one more folder in it. Add a
template that states the rule once and shows only the legal form, assert it is
reported, and give `stated` its own subject the same way. The criterion names the
first; a run that does the work will want both in the same pass.

This is coverage of a guard, not a defect in one: the real templates are compliant
today and the guard's answer about them is right. What is untested is what it
would say about a template that is half-compliant, which is the shape a new
folder's template will actually arrive in.
