---
title: Draw the circular signal before deciding how it bands
status: deferred
opened: 2026-07-28

gated_on: >
  Kendrick deciding to take the flow_direction question — the mockup is the
  cheapest first step of that item, not work of its own

after: [block-signal-free-measures]

reads:
  - docs/todo/block-signal-free-measures.md
  - docs/todo/coverage-and-detection-lanes.md
  - src/sieve/gui/band_plot.py
  - docs/completed-todo/2026.07.27-seeker-upgrades.md
---

# Draw the circular signal before deciding how it bands

**Mockups for representation, never for interaction.** That is the whole rule,
and this repo has evidence on both sides of it.

The one mockup experiment produced a *phantom regression*. `mockups/seeker/`
was never built, and it generated the bug report "we had a beautiful bottom
bar previously but it's now gone" — a regression that never happened, which
cost a session to disprove and ended with the mockup deleted
(`docs/completed-todo/2026.07.27-seeker-upgrades.md`).

It failed because the question was **interaction**. Look at what actually
churned in the bug list before it was deleted: stamp-as-default, hover-to-solo,
click-through navigation, wheel-over-the-panel, crop-handle hit-testing. Every
one is *gesture semantics* — what a drag means versus a click, what happens at
the frame edge — and no static picture can answer those. They need the real
widget under a real hand.

## Where a mockup is genuinely the cheapest instrument

**Representation** questions: what should this quantity *look like*, when
there is no existing form to copy. Two are live.

The stronger one is `docs/todo/block-signal-free-measures.md`, which is
explicitly blocked because "a value band and a heat ramp over an angle are
wrap-around objects the GUI has no shape for". That item is stalled on a
picture nobody has drawn, which makes it the single best candidate in the
tree. `flow_direction` is orthogonal to everything existing and is the
screening's other survivor, so the question is real and not hypothetical.

The other is rule 6's rendering distinctions — absent versus zero, unexamined
versus quiet — which `docs/todo/coverage-and-detection-lanes.md` names as V1's
standing failure and which three unbuilt widgets inherit. That one is weaker
here only because it has no single picture; it is a rule applied per widget.

## The operational rule the seeker taught

**A mockup carries a date and is deleted when its item resolves.** The phantom
regression came from a mockup outliving its question and being read as a
record of something that shipped. If a mockup is checked in, its README says
the date and the item it belongs to, and `tools/doc_refs.py` will flag the
reference once the file is gone — which is how the last dead mockup reference
was found.
