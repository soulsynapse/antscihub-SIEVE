---
title: An undeclarable element refuses every tool the docstring exempts
priority: normal
phase: 7
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests -q -k offering_without_an_element"
opened: 2026-08-09
---

# An undeclarable element refuses every tool the docstring exempts

`offered_tools`' `element` parameter documents its own `None` case:

> `None` where the walk lost it or the stream is a table, and a `None` refuses
> nothing: a position whose elements have no meaning is one where this leg has
> no opinion, not one where every tool is implausible.

The code does the opposite. The element leg is
`node_element(spec.element, element) is None`, and `node_element` returns
`upstream` for `ElementRelation.PRESERVED` — so with `element=None` every
preserving tool resolves to `None` and is refused, as is every aggregator, and
what survives is only a tool declaring a literal `ElementKind`. Against the
scratch shelf in `tests/unit/test_offering.py` the whole array side goes:

    offered_tools(GRAY_FLOAT, None, SHELF)        -> []
    offered_tools(GRAY_FLOAT, ElementKind.PIXEL, SHELF)
                                                  -> aggregator narrow wide

The input is reachable and not exotic: `None` propagates and never recovers
(`node_element`'s own docstring), so every position downstream of an aggregator
over blocks is an element-less position, and the add-tool box there is empty for
a reason that has nothing to do with what the position produces. That is the
second empty-menu cause, distinct from the declaration thinness in
[findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything](../findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md),
and it is a defect rather than a fact about the shelf.

Which side moves is the decision this item carries, and it is small either way.
Making the code match the prose is one clause — skip the element leg entirely
when `element is None`. The alternative is that an aggregator genuinely is
implausible where elements have no meaning, in which case the refusal is right
for aggregators and wrong for preserving tools, and the prose has to say so per
relation rather than as a blanket exemption. What is not defensible is the
current pairing, where the only written statement of the rule denies the
behaviour.

The case belongs in `tests/unit/test_offering.py` beside the element case that
does exist (`test_offering_drops_the_tool_whose_elements_would_lose_their_meaning`),
which passes `PIXEL` and `BLOCK` and never `None`.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k offering_without_an_element
    1036 deselected in 0.86s
    exit: 5

`-k undeclarable_element` was the obvious selector and is green today —
`test_an_undeclarable_element_never_recovers_downstream` in
`tests/unit/test_tool_contract.py` answers to it — so the case name has to
carry `offering` for the criterion to be red for this item's work.

