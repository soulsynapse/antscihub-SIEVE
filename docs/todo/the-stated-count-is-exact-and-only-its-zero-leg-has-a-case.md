---
title: The guard demands the rule be stated exactly once, and only the zero side of that has a subject
priority: normal
phase: "00"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/docs/test_doc_index.py -q -k \"states_the_rule_twice\""
opened: 2026-08-07
---

# The guard demands the rule be stated exactly once, and only the zero side of that has a subject

`_silent` in `tests/docs/test_doc_index.py` reports a template whose
`(stated, bool(legal), bool(illegal))` is not `(1, True, True)`. `9d7c166` gave
`stated` its first subject with `UNSTATED_TEMPLATE`, which states it 0 times, so
the guard now has a case for the difference between none and one. It has none for
the difference between one and two: replacing `shown.stated` with
`bool(shown.stated)` and the tuple's `1` with `True` leaves the whole module at 80
passed. A template that states the rule in two places is reported today, and
nothing in the tree says whether that is the rule or an accident of how the
expression was written.

Either resolution closes this, and the criterion takes both: give the leg a
subject that states the rule twice and assert what the guard says about it, or
decide that exactness was never meant — the guard exists so that no template
teaches by prose alone or by example alone, and saying it twice is neither
failure — and relax the comparison, with the same subject asserting it is not
reported. What must not survive is a third element carrying an exactness no case
has ever exercised.
