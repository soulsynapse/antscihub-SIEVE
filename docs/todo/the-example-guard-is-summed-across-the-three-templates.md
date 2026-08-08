---
title: The template example guard counts across all three, and the todo template shows neither form
priority: high
phase: "00"
status: open
gated_on: nothing
done_when: "uv run pytest \"tests/docs/test_doc_index.py::test_each_template_shows_both_forms\" -q"
opened: 2026-08-07
---

# The template example guard counts across all three, and the todo template shows neither form

`6f3cfc8` closed the anti-vacuity hole it could see — a rewrite that satisfied
the construction check by deleting every example — with

```python
assert (stated, bool(legal), bool(illegal)) == (3, True, True)
```

and the comment above it: "The three of them state the rule and show both
forms; a rewrite that deleted the examples would satisfy everything above and
teach nothing." `stated` is per-template and holds. `legal` and `illegal` are
summed over the three folders and then collapsed to booleans, so they say only
that *somewhere* in the corpus one example of each kind survives. Counted per
file today:

| template | stated | legal examples | illegal examples |
|---|---|---|---|
| todo | 1 | 0 | 0 |
| findings | 1 | 3 | 1 |
| adr | 1 | 3 | 1 |

So the sentence is already false of the tree it was committed with: the todo
template shows neither form. It states the rule and then points at a field
(``which is what `done_when` below is``) instead of showing the ordinary quoted
form as a `key: value` a reader would copy — and that is the template an author
reads most often. Two of the three could delete every example and the guard
would stay green.

This is the shape
`findings/loop/2026.08.06-one-red-per-contract-certifies-the-contract-not-its-lines.md`
names: a sample quantified over the corpus, read as quantified over each of its
members. The repair is the same in both directions — make the guard per
template, and give the todo template the two examples the guard would then
demand.

`done_when` names a test that does not exist yet, so it is red for the right
reason today. Write it first, against the templates as they stand, and it must
go red on `todo` before the template gains its two examples; the summed
assertion in the existing test is then redundant and should go rather than sit
beside a stronger one.
