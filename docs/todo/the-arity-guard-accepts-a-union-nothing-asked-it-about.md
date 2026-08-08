---
title: The arity guard's union and variadic branches have no case
priority: low
phase: 7
status: done
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -q -k arity_the_shelf_does_not_declare"
opened: 2026-08-08
---

# The arity guard's union and variadic branches have no case

`_value_components` reduces a union by `min` — so a field that could be
populated as a scalar makes the whole field one component — and counts a
variadic `tuple[X, ...]` as one rather than as a whole value of unknown length.
Both are argued in its docstring; neither is held by anything. `max` in place of
`min` and the variadic branch deleted both survive `uv run pytest -q tests/unit`
(`findings/2026.08.08-the-arity-guards-two-hardest-branches-are-the-two-nothing-holds.md`).

The reason is structural rather than an oversight: the only union on the shelf
is `detect.count_frac`, `tuple[float, float] | None`, and `NoneType` is filtered
before the reduction, so exactly one branch reaches it and every reduction over
one branch is the same function. No params model annotates a variadic tuple at
all. The acceptance half of
`test_every_composite_stereotype_reads_the_annotation_it_stands_over` says in a
comment that "every branch of it is asked rather than the first" — true of the
code, and its fixture has one branch to ask.

Two refusal cases close it, both on annotations no tool declares, which is the
point: a composite kind on `int | tuple[int, int]`, and a composite kind on
`tuple[int, ...]`. Naming them for the shelf they are absent from is what keeps
the next reader from deleting them as redundant with the shapes already tested.

## Split, 2026-08-08

The `ENUM`-at-registration and `_dereference` `$ref` paragraphs 07.5 added here
in review of `b19599f` are `enum-is-refused-by-nothing-at-registration.md`,
which carries them in full. `5819504` wrote them into that item and left them
here as well; this review removed the copy, because this item's criterion never
selected on them and a `done` item holding open work in its body is a second
place to read the same claim.

The variadic rule's spelling is the open question the finding records: the
docstring argues an editor drawing a fixed number of handles cannot be handed an
unbounded length, which reads as an argument for refusing a variadic composite
outright rather than for counting it as one component. The two agree on the
refusal this item asks for and diverge only if `SCALAR_RANGE` is ever declared
on a variadic field, so the case can be written before that is settled.
