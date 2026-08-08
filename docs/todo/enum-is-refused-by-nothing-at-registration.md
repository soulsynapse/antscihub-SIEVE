---
title: ENUM is checked for nothing at registration, and a $ref nothing writes decides a branch
priority: low
phase: 7
status: open
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -q -k 'enum_over_an_annotation_with_no_choices or a_pointer_pydantic_does_not_write'"
opened: 2026-08-08
---

# ENUM is checked for nothing at registration, and a $ref nothing writes decides a branch

Split off `the-arity-guard-accepts-a-union-nothing-asked-it-about.md`, which
carried these two beside the arity cases and whose criterion selects only on the
arity ones. Both are the same shape as the two that item closed — a branch of
`core/tool_base.py` no tool on the shelf can disagree with — and differ in that
the first wants a refusal the module does not yet make.

`_ONE_FIELD_STEREOTYPES` admits `ENUM` beside `SCALAR_RANGE` and nothing asks
whether the annotation under it can be enumerated at all, while
`param_form`'s generator falls back to `described.get("enum", (True, False))`.
So a `str` field declared `ENUM` gets a two-item True/False drop list rather
than a refusal — the one silent degradation in a module whose whole argument is
that an unmapped kind is loud. `_closed_values` already answers the question for
a `StrEnum`, and `bool` is the other annotation the fallback is right about; the
refusal is the third case, over an annotation that is neither.

`_dereference` argues in its docstring that a `$ref` it does not understand
degrades to the unresolved property rather than raising, and
`if not ref.startswith(prefix): ==> if False:` survives
`tests/unit/test_inspect_cmd.py` and `tests/gui/test_param_generator.py`
because pydantic writes no other pointer
(`findings/2026.08.08-the-arity-guards-two-hardest-branches-are-the-two-nothing-holds.md`
records the sibling pair). A case over a schema built by hand rather than by
pydantic is what holds it; if writing one shows the branch cannot be reached
by any schema the shelf produces *or* by one a caller could hand it, the branch
is the thing to delete and the docstring's argument goes with it. Which of the
two it is is the open half of this item.
