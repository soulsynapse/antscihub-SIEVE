---
title: Whether a stereotype declares an arity, since the two interval kinds disagree about it
status: deferred
deferred_for: decision
gated_on: Kendrick deciding whether the stereotype map answers "how many params make one widget" — a pairing rule the generator is answerable to, a pair-shaped `SPAN`, or a second declaration `adr/declared-means-verified.md` will not admit before a reader exists
priority: normal
phase: 7
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
