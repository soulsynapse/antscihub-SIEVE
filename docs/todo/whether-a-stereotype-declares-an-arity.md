---
title: A composite stereotype sits on the field that holds the whole value
step: "07.1"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_tool_contract.py -q -k composite_stereotype && uv run pytest tests/unit/test_span.py -q"
opened: 2026-08-07
---

# Whether a stereotype declares an arity

`BAND` landed (`a-band-has-no-stereotype-of-its-own.md`) with a member comment
reading "an ordered lo/hi pair on a value axis", and `detect`'s three `BAND`
params are each a `tuple[float, float]` — one param, one whole interval.
`SPAN`'s only production user is `tools/span.py`, whose `start` and `end` are
two separate `int` fields both declared `SPAN`, under a comment saying so
deliberately: both bounds carry one stereotype because they are one populated
value.

So the map carries two arities under names that read parallel. A generator
meeting `SPAN` holds one half of an interval and has to find the other half —
by adjacency, by name, by something the spec does not say. Meeting `BAND` it
has to know the opposite. Nothing in `ToolSpec` distinguishes the two, and
`adr/declared-means-verified.md`'s stand-in consumer refuses an unknown kind by
name and has no opinion about how many fields wear one.

Neither declaration is wrong about its own tool. The gap is that the vocabulary
answers "what kind of value is this" while the generator also needs "how many
params make one widget", and the second question is answered by a comment in
one tool and by a type in another.

Three shapes are live and this item picks none of them:

- The generator groups by stereotype within a tool, and the pairing rule is
  written once in `ParamStereotype`'s docstring as a rule the generator is
  answerable to rather than a convention each tool restates.
- `SPAN` becomes pair-shaped like `BAND`, which makes `span.py`'s two ints one
  tuple field and costs a schema change and a plan-fold rewrite.
- Arity becomes its own declaration — the same second declaration
  `a-band-has-no-stereotype-of-its-own.md` refused for the axis, and refused on
  the same grounds: no reader.

It is answerable only against Phase 7's generator, which is where
`a-composite-parameter-prints-no-shape-and-no-bounds.md` also waits on a
reader, and the two may be one ruling.

## Ruled 2026-08-08 — `adr/one-field-is-one-populated-value.md`

The third shape is the one taken, in the form the item did not list: arity
becomes a property of the *field* rather than a second declaration beside the
kind, so nothing new is declared and nothing has to be kept in agreement. A
composite kind must sit on the annotation that holds the whole value, and
registration reads `params_model` to prove it — which is why this needed no
generator to become checkable.

`span` is what that costs: one pair-shaped parameter in place of two bounds,
`selected_frames` folding the pair it is handed, `primary_params` and the
caption collapsing to one entry each, and `tests/unit/test_span.py`'s
constructors rewritten. Editing a ported test is a decision under the porting
discipline; the ADR is where that decision is recorded, so this item carries it
out rather than taking it.

The argument that moved it was not the generator. A timeline drag is one
gesture, and a value split across two fields makes it two commands and one
intermediate state the model's own validator refuses — so the split would have
reached the undo stacks, not just the widget. `a-composite-parameter-prints-no-shape-and-no-bounds.md`
stays a separate item: it is about reading bounds through an `anyOf`, which
this rule makes more load-bearing rather than answering.

One observation this ruling leaves standing: `POINT` is a member no tool
declares, admitted for a stamp tool that does not exist. Cheap for an enum
member, and not worth its own item, but it is `adr/declared-means-verified.md`
bent inside the vocabulary that rule is enforced through.
